"""API météo simulée, au format Open-Meteo /v1/forecast."""
import json
import os
import random
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

HOT_LAT = os.environ.get("HOT_LAT", "")  # ex. "43.30" : 38 °C forcés pour cette latitude
UNITS = {"temperature_2m": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h"}


def build_payload(lat: float, lon: float, fields: list) -> dict:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    slot = now.replace(minute=now.minute - now.minute % 15)  # créneau de 15 min
    rnd = random.Random(f"{lat}:{lon}:{slot.isoformat()}")
    values = {
        "temperature_2m": round(rnd.uniform(5, 25), 1),
        "relative_humidity_2m": rnd.randint(30, 95),
        "wind_speed_10m": round(rnd.uniform(0, 40), 1),
    }
    if HOT_LAT and abs(lat - float(HOT_LAT)) < 0.01:
        values["temperature_2m"] = 38.0
    current = {"time": slot.strftime("%Y-%m-%dT%H:%M"), "interval": 900}
    current_units = {"time": "iso8601", "interval": "seconds"}
    for field in fields:
        if field in values:
            current[field] = values[field]
            current_units[field] = UNITS[field]
    return {
        "latitude": lat,
        "longitude": lon,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "current_units": current_units,
        "current": current,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return self.send_json(200, {"status": "ok"})
        if url.path != "/v1/forecast":
            return self.send_json(404, {"error": True, "reason": "not found"})
        query = parse_qs(url.query)
        try:
            lat = float(query["latitude"][0])
            lon = float(query["longitude"][0])
        except (KeyError, ValueError):
            return self.send_json(400, {"error": True, "reason": "latitude/longitude manquants"})
        fields = query.get("current", [""])[0].split(",")
        return self.send_json(200, build_payload(lat, lon, fields))

    def send_json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
