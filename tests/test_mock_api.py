import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mock_app", ROOT / "mock-api" / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

FIELDS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"]


def test_format_open_meteo():
    payload = app.build_payload(48.85, 2.35, FIELDS)
    assert set(FIELDS) <= set(payload["current"])
    assert len(payload["current"]["time"]) == 16  # AAAA-MM-JJTHH:MM, attendu par NiFi


def test_champs_filtres():
    payload = app.build_payload(48.85, 2.35, ["temperature_2m"])
    assert "wind_speed_10m" not in payload["current"]
