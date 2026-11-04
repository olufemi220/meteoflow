from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
ENVS = ["local", "dev", "staging", "prod"]
REQUIRED = {"api_base_url", "api_fields", "alert_temp_max", "mongo_uri",
            "mongo_database", "mongo_user", "pg_url", "pg_user"}


def load(env):
    return yaml.safe_load((ROOT / "config" / f"{env}.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("env", ENVS)
def test_parametres_obligatoires(env):
    cfg = load(env)
    assert REQUIRED <= set(cfg["parameters"])
    assert {"mongo_password", "pg_password"} <= set(cfg["sensitive"])


@pytest.mark.parametrize("env", ENVS)
def test_villes_valides(env):
    cities = load(env)["cities"]
    names = [c["city"] for c in cities]
    assert cities, "au moins une ville"
    assert len(names) == len(set(names)), "villes en double"
    for c in cities:
        assert -90 <= c["lat"] <= 90 and -180 <= c["lon"] <= 180


def test_seuil_alerte_numerique():
    for env in ENVS:
        float(load(env)["parameters"]["alert_temp_max"])
