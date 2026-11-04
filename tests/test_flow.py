import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FLOW_FILE = ROOT / "flows" / "meteoflow.json"

if not FLOW_FILE.exists():
    pytest.skip("flows/meteoflow.json pas encore exporté (étape 6 D)", allow_module_level=True)

FLOW = json.loads(FLOW_FILE.read_text(encoding="utf-8"))


def processors(group):
    yield from group.get("processors", [])
    for child in group.get("processGroups", []):
        yield from processors(child)


def test_processeurs_attendus():
    types = {p["type"].split(".")[-1] for p in processors(FLOW["flowContents"])}
    for expected in ["GenerateFlowFile", "SplitJson", "EvaluateJsonPath", "InvokeHTTP",
                     "JoltTransformJSON", "PutMongoRecord", "ValidateRecord",
                     "PutDatabaseRecord", "RouteOnAttribute"]:
        assert expected in types, f"{expected} manquant"


def test_aucune_valeur_en_dur():
    text = json.dumps(FLOW["flowContents"])
    for forbidden in ["api.open-meteo.com", "mock-api:8080", "jdbc:postgresql://", "mongodb://", "meteo_pwd"]:
        assert forbidden not in text, f"{forbidden} doit passer par un paramètre"


def test_url_api_parametree():
    http = next(p for p in processors(FLOW["flowContents"]) if p["type"].endswith("InvokeHTTP"))
    url = next(v for v in http["properties"].values() if v and "/v1/forecast" in v)
    assert "#{api_base_url}" in url and "#{api_fields}" in url and "${lat}" in url
