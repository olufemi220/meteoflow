"""Déploie le flux MétéoFlow dans NiFi 2.x via l'API REST.

Exemple : python scripts/deploy_flow.py --env dev
Variables requises : NIFI_USER, NIFI_PASSWORD et celles de la section
« sensitive » de config/<env>.yaml.
"""
import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent.parent
FLOW_FILE = ROOT / "flows" / "meteoflow.json"
PG_NAME = "MeteoFlow"
CLIENT_ID = str(uuid.uuid4())


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Variable d'environnement manquante : {name}")
    return value


def load_config(env: str) -> dict:
    cfg = yaml.safe_load((ROOT / "config" / f"{env}.yaml").read_text(encoding="utf-8"))
    params = {name: (str(value), False) for name, value in cfg["parameters"].items()}
    params["cities"] = (json.dumps(cfg["cities"], ensure_ascii=False), False)
    for name, env_var in cfg.get("sensitive", {}).items():
        params[name] = (require_env(env_var), True)
    return {"url": cfg["nifi"]["url"], "params": params}


class Nifi:
    def __init__(self, url: str, user: str, password: str):
        self.api = url.rstrip("/") + "/nifi-api"
        self.http = requests.Session()
        self.http.verify = False  # certificat auto-signé de NiFi
        self.login(user, password)

    def login(self, user: str, password: str, attempts: int = 40):
        for i in range(attempts):
            try:
                r = self.http.post(f"{self.api}/access/token",
                                   data={"username": user, "password": password}, timeout=10)
                if r.status_code == 201:
                    self.http.cookies.clear()
                    self.http.headers["Authorization"] = f"Bearer {r.text}"
                    return
                print(f"Connexion refusée ({r.status_code}), nouvel essai...")
            except requests.RequestException:
                print(f"NiFi pas encore prêt ({i + 1}/{attempts})...")
            time.sleep(10)
        sys.exit("Impossible de se connecter à NiFi.")

    def call(self, method: str, path: str, check: bool = True, **kwargs):
        r = self.http.request(method, self.api + path, timeout=60, **kwargs)
        if check and r.status_code >= 400:
            sys.exit(f"{method} {path} -> {r.status_code} : {r.text}")
        return r

    def get(self, path: str) -> dict:
        return self.call("GET", path).json()

    def put(self, path: str, body: dict) -> dict:
        return self.call("PUT", path, json=body).json()


def wait(condition, what: str, timeout: int = 180):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return
        time.sleep(3)
    sys.exit(f"Délai dépassé : {what}")


def find_group(nifi: Nifi, root_id: str):
    flow = nifi.get(f"/flow/process-groups/{root_id}")
    for pg in flow["processGroupFlow"]["flow"]["processGroups"]:
        if pg["component"]["name"] == PG_NAME:
            return pg["id"]
    return None


def services(nifi: Nifi, pg_id: str) -> list:
    return nifi.get(f"/flow/process-groups/{pg_id}/controller-services"
                    "?includeAncestorGroups=false&includeDescendantGroups=true")["controllerServices"]


def set_services(nifi: Nifi, pg_id: str, state: str):
    body = {"id": pg_id, "state": state}
    wait(lambda: nifi.call("PUT", f"/flow/process-groups/{pg_id}/controller-services",
                           check=False, json=body).ok, f"services -> {state}")
    def done() -> bool:
        return all(s["component"]["state"] == state for s in services(nifi, pg_id))

    end = time.time() + 180
    while time.time() < end:
        if done():
            return
        time.sleep(3)
    details = [f"{s['component']['name']} : {s['component']['state']} {s['component'].get('validationErrors') or ''}"
               for s in services(nifi, pg_id)]
    sys.exit(f"Délai dépassé : services -> {state}\n" + "\n".join(details))


def all_stopped(nifi: Nifi, pg_id: str) -> bool:
    procs = nifi.get(f"/process-groups/{pg_id}/processors")["processors"]
    return all(p["component"]["state"] != "RUNNING"
               and p["status"]["aggregateSnapshot"].get("activeThreadCount", 0) == 0 for p in procs)


def remove_group(nifi: Nifi, pg_id: str):
    print("Arrêt et suppression de l'ancienne version...")
    nifi.put(f"/flow/process-groups/{pg_id}", {"id": pg_id, "state": "STOPPED"})
    wait(lambda: all_stopped(nifi, pg_id), "arrêt complet des processeurs")
    set_services(nifi, pg_id, "DISABLED")
    drop = nifi.call("POST", f"/process-groups/{pg_id}/empty-all-connections-requests").json()
    drop_url = f"/process-groups/{pg_id}/empty-all-connections-requests/{drop['dropRequest']['id']}"
    wait(lambda: nifi.get(drop_url)["dropRequest"]["finished"], "vidage des files")
    nifi.call("DELETE", drop_url)

    last_error = {"text": ""}

    def try_delete() -> bool:
        version = nifi.get(f"/process-groups/{pg_id}")["revision"]["version"]
        url = f"/process-groups/{pg_id}?version={version}&clientId={CLIENT_ID}"
        r = nifi.call("DELETE", url, check=False)
        last_error["text"] = r.text[:300]
        return r.ok

    end = time.time() + 180
    while not try_delete():
        if time.time() > end:
            sys.exit(f"Délai dépassé : suppression de l'ancien groupe ({last_error['text']})")
        time.sleep(3)


def recreate_context(nifi: Nifi, name: str, params: dict) -> str:
    for ctx in nifi.get("/flow/parameter-contexts")["parameterContexts"]:
        if ctx["component"]["name"] == name:
            version = ctx["revision"]["version"]
            nifi.call("DELETE", f"/parameter-contexts/{ctx['id']}?version={version}&clientId={CLIENT_ID}")
    body = {
        "revision": {"version": 0, "clientId": CLIENT_ID},
        "component": {"name": name, "parameters": [
            {"parameter": {"name": k, "value": v, "sensitive": s}} for k, (v, s) in params.items()
        ]},
    }
    return nifi.call("POST", "/parameter-contexts", json=body).json()["id"]


def strip_context_names(group: dict):
    group.pop("parameterContextName", None)
    for child in group.get("processGroups", []):
        strip_context_names(child)


def upload_flow(nifi: Nifi, root_id: str) -> str:
    flow = json.loads(FLOW_FILE.read_text(encoding="utf-8"))
    flow.pop("parameterContexts", None)  # le contexte vient de config/<env>.yaml
    strip_context_names(flow["flowContents"])
    files = {"file": ("meteoflow.json", json.dumps(flow).encode(), "application/json")}
    data = {"groupName": PG_NAME, "positionX": "0", "positionY": "0",
            "clientId": CLIENT_ID, "disconnectedNodeAcknowledged": "false"}
    r = nifi.call("POST", f"/process-groups/{root_id}/process-groups/upload", files=files, data=data)
    return r.json()["id"]


def check_valid(nifi: Nifi, pg_id: str):
    time.sleep(5)  # NiFi revalide les composants en arrière-plan
    errors = []
    for proc in nifi.get(f"/process-groups/{pg_id}/processors")["processors"]:
        for err in proc["component"].get("validationErrors") or []:
            errors.append(f"{proc['component']['name']} : {err}")
    if errors:
        sys.exit("Processeurs invalides :\n" + "\n".join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=["local", "dev", "staging", "prod"])
    args = parser.parse_args()

    if not FLOW_FILE.exists():
        sys.exit("flows/meteoflow.json introuvable : exportez d'abord le flux depuis NiFi (étape 6 D).")

    cfg = load_config(args.env)
    nifi = Nifi(cfg["url"], require_env("NIFI_USER"), require_env("NIFI_PASSWORD"))
    root_id = nifi.get("/flow/process-groups/root")["processGroupFlow"]["id"]

    old_id = find_group(nifi, root_id)
    if old_id:
        remove_group(nifi, old_id)

    ctx_id = recreate_context(nifi, f"meteoflow-{args.env}", cfg["params"])
    pg_id = upload_flow(nifi, root_id)
    pg = nifi.get(f"/process-groups/{pg_id}")
    nifi.put(f"/process-groups/{pg_id}", {
        "revision": pg["revision"],
        "component": {"id": pg_id, "parameterContext": {"id": ctx_id}},
    })

    print("Activation des services...")
    set_services(nifi, pg_id, "ENABLED")
    check_valid(nifi, pg_id)
    nifi.put(f"/flow/process-groups/{pg_id}", {"id": pg_id, "state": "RUNNING"})
    print(f"Flux MétéoFlow déployé et démarré ({args.env}).")


if __name__ == "__main__":
    main()
