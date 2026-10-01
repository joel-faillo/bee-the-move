"""Optional map context from MeteoSwiss automatic pollen observations.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

import csv
import io

from services.geo import haversine_km
from services.http import HttpClient

COLLECTION = "ch.meteoschweiz.ogd-pollen"
ITEMS_URL = f"https://data.geo.admin.ch/api/stac/v1/collections/{COLLECTION}/items"


class PollenService:
    """Read the nearest current MeteoSwiss pollen station.

    Pollen is map context only: airborne grains do not measure nectar supply,
    so this service intentionally contributes no regional-index points.
    """

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def latest_near(self, lat: float, lon: float) -> dict:
        data = self.http.get_json(ITEMS_URL, params={"limit": 50})
        stations = [item for item in data.get("features", []) if self._now_asset(item)]
        if not stations:
            return {"available": False, "reason": "Nessuna misura oraria corrente"}
        station = min(stations, key=lambda item: self._distance(item, lat, lon))
        asset = self._now_asset(station)
        text = self.http.get_text(asset["href"], encoding="latin-1", cache=False)
        rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
        if not rows:
            return {"available": False, "reason": "File pollini vuoto"}
        latest = rows[-1]
        values = {
            key: float(value)
            for key, value in latest.items()
            if key not in {"station_abbr", "reference_timestamp"}
            and value not in (None, "")
        }
        total = round(sum(values.values()), 1)
        station_lon, station_lat = station["geometry"]["coordinates"]
        return {
            "available": True,
            "station": station["properties"]["title"],
            "station_distance_km": round(self._distance(station, lat, lon), 1),
            "timestamp": latest.get("reference_timestamp"),
            "lat": station_lat,
            "lon": station_lon,
            "total_pollen_m3": total,
            "measurements": values,
            "note": "Indicatore osservativo, non una misura diretta del nettare",
        }

    @staticmethod
    def _now_asset(item: dict) -> dict | None:
        return next(
            (
                asset
                for name, asset in item.get("assets", {}).items()
                if name.endswith("_h_now.csv")
            ),
            None,
        )

    @staticmethod
    def _distance(item: dict, lat: float, lon: float) -> float:
        station_lon, station_lat = item["geometry"]["coordinates"]
        return haversine_km(lat, lon, station_lat, station_lon)
