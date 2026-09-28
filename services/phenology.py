"""MeteoSwiss phenological-observation adapter.

This is observation data, not an official site-level flowering forecast. The
app therefore reports a flowering *signal*: three nearby stations, the current
season when available, and a ten-year median for gaps.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

import csv
import io
import math
from datetime import date, datetime
from statistics import median

from services.geo import haversine_km
from services.http import HttpClient

COLLECTION = "ch.meteoschweiz.ogd-phenology"
ITEMS_URL = f"https://data.geo.admin.ch/api/stac/v1/collections/{COLLECTION}/items"
PARAMETERS_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-phenology/ogd-phenology_meta_parameters.csv"


class PhenologyService:
    def __init__(self, http: HttpClient, station_count: int = 3) -> None:
        self.http = http
        self.station_count = station_count

    def flowering_forecast(self, lat: float, lon: float, dates: list[str]) -> dict:
        """Estimate proximity to observed 50% flowering dates."""
        estimates: dict[str, list[tuple[float, float, bool]]] = {}
        station_details = []
        fields = self._flowering_fields()
        for station in self._nearest_stations(lat, lon):
            asset = next(iter(station.get("assets", {}).values()), None)
            if not asset:
                continue
            distance = haversine_km(
                lat,
                lon,
                station["geometry"]["coordinates"][1],
                station["geometry"]["coordinates"][0],
            )
            observed = self._station_estimates(asset["href"], fields)
            if not observed:
                continue
            station_details.append(
                {
                    "name": station["properties"]["title"],
                    "distance_km": round(distance, 1),
                }
            )
            weight = 1 / (1 + distance / 25)
            for field, (day_of_year, current) in observed.items():
                estimates.setdefault(field, []).append((day_of_year, weight, current))

        peaks = {
            field: sum(day * weight for day, weight, _ in values)
            / sum(weight for _, weight, _ in values)
            for field, values in estimates.items()
        }
        if not peaks:
            return {
                "available": False,
                "reason": "Osservazioni di fioritura insufficienti",
                "daily": [],
                "score": 0,
            }

        daily = []
        for value in dates:
            target = date.fromisoformat(value).timetuple().tm_yday
            signals = sorted(
                (math.exp(-abs(target - expected) / 14) for expected in peaks.values()),
                reverse=True,
            )[:6]
            daily.append(
                {"date": value, "score": round(100 * sum(signals) / len(signals))}
            )
        current_fields = sum(
            any(current for _, _, current in values) for values in estimates.values()
        )
        return {
            "available": True,
            "stations": station_details,
            "station": ", ".join(item["name"] for item in station_details),
            "daily": daily,
            "score": (
                round(sum(day["score"] for day in daily) / len(daily)) if daily else 0
            ),
            "observed_current_season": current_fields,
            "method": "3 stazioni vicine; anno corrente se disponibile, altrimenti mediana degli ultimi 10 anni",
        }

    def nearest_station(self, lat: float, lon: float) -> dict | None:
        """Return the nearest observation station for transparent map context.

        The trained model uses the national historical network, so this point
        is labelled as a nearby reference station rather than as the sole
        source of a candidate's prediction.
        """
        stations = self._nearest_stations(lat, lon)
        if not stations:
            return None
        station = stations[0]
        station_lon, station_lat = station["geometry"]["coordinates"]
        return {
            "name": station.get("properties", {}).get("title", "Phenology station"),
            "lat": station_lat,
            "lon": station_lon,
            "distance_km": round(haversine_km(lat, lon, station_lat, station_lon), 1),
            "note": "Nearest MeteoSwiss observation station; the model uses the national historical network.",
        }

    def _nearest_stations(self, lat: float, lon: float) -> list[dict]:
        data = self.http.get_json(ITEMS_URL, params={"limit": 200})
        stations = [
            item
            for item in data.get("features", [])
            if item.get("geometry", {}).get("coordinates") and item.get("assets")
        ]
        stations.sort(
            key=lambda item: haversine_km(
                lat,
                lon,
                item["geometry"]["coordinates"][1],
                item["geometry"]["coordinates"][0],
            )
        )
        return stations[: self.station_count]

    def _flowering_fields(self) -> set[str]:
        text = self.http.get_text(PARAMETERS_URL, encoding="latin-1")
        fields = set()
        for row in csv.DictReader(io.StringIO(text), delimiter=";"):
            if "flowering (50%)" in row.get("parameter_description_en", "").lower():
                fields.add(row["parameter_shortname"])
        return fields

    def _station_estimates(
        self, url: str, fields: set[str]
    ) -> dict[str, tuple[float, bool]]:
        rows = list(
            csv.DictReader(
                io.StringIO(self.http.get_text(url, encoding="latin-1")), delimiter=";"
            )
        )
        current_year = date.today().year
        result = {}
        for field in fields:
            values: list[tuple[int, float]] = []
            for row in rows:
                try:
                    observed = datetime.strptime(row.get(field, ""), "%Y%m%d").date()
                except ValueError:
                    continue
                values.append((observed.year, float(observed.timetuple().tm_yday)))
            current = next(
                (day for year, day in reversed(values) if year == current_year), None
            )
            if current is not None:
                result[field] = (current, True)
            elif values:
                result[field] = (median(day for _, day in values[-10:]), False)
        return result
