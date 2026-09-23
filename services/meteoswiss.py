"""MeteoSwiss local-forecast adapter.

The STAC collection stores one national CSV per parameter. This adapter keeps
only requested points and derives flight suitability from hourly temperature,
rain, wind, gusts and global radiation. Radiation avoids double-counting
correlated sunshine and cloud information.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from zoneinfo import ZoneInfo

from services.geo import haversine_km
from services.http import HttpClient

COLLECTION = "ch.meteoschweiz.ogd-local-forecasting"
STAC_ITEMS = f"https://data.geo.admin.ch/api/stac/v1/collections/{COLLECTION}/items"
POINTS_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting/ogd-local-forecasting_meta_point.csv"
SWISS_TIME = ZoneInfo("Europe/Zurich")


@dataclass(frozen=True)
class ForecastPoint:
    point_id: str
    point_type_id: str
    name: str
    postal_code: str
    lat: float
    lon: float
    easting: float
    northing: float
    metadata_height: float | None
    distance_km: float

    @property
    def key(self) -> tuple[str, str]:
        return self.point_id, self.point_type_id


class MeteoSwissForecastService:
    # Radiation captures usable light without double-counting sunshine and cloud cover.
    PARAMETERS = ("tre200h0", "rre150h0", "fu3010h0", "fu3010h1", "gre000h0")

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def candidates(
        self, lat: float, lon: float, radius_km: float, limit: int
    ) -> list[ForecastPoint]:
        text = self.http.get_text(POINTS_URL, encoding="latin-1")
        points: list[ForecastPoint] = []
        for row in csv.DictReader(io.StringIO(text), delimiter=";"):
            if row.get("point_type_id") != "2":
                continue
            distance = haversine_km(
                lat,
                lon,
                float(row["point_coordinates_wgs84_lat"]),
                float(row["point_coordinates_wgs84_lon"]),
            )
            if distance <= radius_km:
                points.append(
                    ForecastPoint(
                        point_id=row["point_id"],
                        point_type_id=row["point_type_id"],
                        name=row["point_name"].strip(),
                        postal_code=row["postal_code"].strip(),
                        lat=float(row["point_coordinates_wgs84_lat"]),
                        lon=float(row["point_coordinates_wgs84_lon"]),
                        easting=float(row["point_coordinates_lv95_east"]),
                        northing=float(row["point_coordinates_lv95_north"]),
                        metadata_height=_float_or_none(row.get("point_height_masl")),
                        distance_km=round(distance, 1),
                    )
                )
        unique: dict[str, ForecastPoint] = {}
        for point in sorted(points, key=lambda item: item.distance_km):
            unique.setdefault(point.name.casefold(), point)
        available = list(unique.values())
        if len(available) <= limit:
            return available
        step = (len(available) - 1) / (limit - 1)
        return [available[round(index * step)] for index in range(limit)]

    def forecasts(self, points: list[ForecastPoint]) -> tuple[dict, dict]:
        """Return nine daily summaries built from the latest hourly forecast."""
        item = self._latest_populated_item()
        assets = item.get("assets", {})
        urls = {
            parameter: self._latest_asset_url(assets, parameter)
            for parameter in self.PARAMETERS
        }
        keys = {point.key for point in points}
        values = {
            parameter: self._read_parameter(url, keys)
            for parameter, url in urls.items()
        }
        combined: dict[tuple[str, str], list[dict]] = {}
        for key in keys:
            timestamps = sorted(
                set().union(*(values[p].get(key, {}) for p in self.PARAMETERS))
            )
            grouped: dict[str, list[dict]] = {}
            for timestamp in timestamps:
                local = datetime.fromisoformat(timestamp).astimezone(SWISS_TIME)
                hour = {
                    "time": local.isoformat(timespec="minutes"),
                    "temperature": values["tre200h0"].get(key, {}).get(timestamp),
                    "rain_mm": values["rre150h0"].get(key, {}).get(timestamp),
                    "wind_kmh": values["fu3010h0"].get(key, {}).get(timestamp),
                    "gust_kmh": values["fu3010h1"].get(key, {}).get(timestamp),
                    "radiation_wm2": values["gre000h0"].get(key, {}).get(timestamp),
                }
                grouped.setdefault(local.date().isoformat(), []).append(hour)
            summaries = [
                self._summarise_day(day, hours)
                for day, hours in sorted(grouped.items())
            ]
            combined[key] = [day for day in summaries if day["flight_hours"] > 0][:9]
        return combined, {
            "item": item.get("id"),
            "updated": item.get("properties", {}).get("updated"),
            "parameters": list(self.PARAMETERS),
            "resolution": "hourly",
        }

    @staticmethod
    def _summarise_day(day: str, hours: list[dict]) -> dict:
        # Radiation identifies usable daylight across seasons better than a
        # fixed clock window.
        daylight = [hour for hour in hours if (hour.get("radiation_wm2") or 0) >= 20]
        scored = [_flight_hour_score(hour) for hour in daylight]
        return {
            "date": day,
            "temperature": _average(hour.get("temperature") for hour in daylight),
            "rain_mm": round(sum(hour.get("rain_mm") or 0 for hour in daylight), 1),
            "wind_kmh": _average(hour.get("wind_kmh") for hour in daylight),
            "gust_kmh": _average(hour.get("gust_kmh") for hour in daylight),
            "radiation_wm2": _average(hour.get("radiation_wm2") for hour in daylight),
            "flight_hours": len(daylight),
            "favourable_hours": sum(score >= 60 for score in scored),
            "flight_score": round(mean(scored), 1) if scored else 0,
        }

    def _latest_populated_item(self) -> dict:
        data = self.http.get_json(
            STAC_ITEMS, params={"sortby": "-properties.datetime", "limit": 7}
        )
        for item in data.get("features", []):
            if item.get("assets"):
                return item
        raise RuntimeError("Nessun asset MeteoSwiss Local Forecast disponibile")

    @staticmethod
    def _latest_asset_url(assets: dict, parameter: str) -> str:
        matches = [
            asset
            for name, asset in assets.items()
            if name.endswith(f".{parameter}.csv")
        ]
        if not matches:
            raise RuntimeError(f"Parametro MeteoSwiss non disponibile: {parameter}")
        return max(
            matches, key=lambda asset: asset.get("updated", asset.get("created", ""))
        )["href"]

    def _read_parameter(self, url: str, wanted: set[tuple[str, str]]) -> dict:
        text = self.http.get_text(url, encoding="latin-1")
        result: dict[tuple[str, str], dict[str, float | None]] = {}
        for row in csv.DictReader(io.StringIO(text), delimiter=";"):
            key = row.get("point_id", ""), row.get("point_type_id", "")
            if key not in wanted:
                continue
            try:
                timestamp = (
                    datetime.strptime(row.get("Date", ""), "%Y%m%d%H%M")
                    .replace(tzinfo=timezone.utc)
                    .isoformat()
                )
            except ValueError:
                continue
            value_key = next(
                (
                    name
                    for name in row
                    if name not in {"point_id", "point_type_id", "Date"}
                ),
                None,
            )
            result.setdefault(key, {})[timestamp] = (
                _float_or_none(row.get(value_key)) if value_key else None
            )
        return result


def _flight_hour_score(hour: dict) -> float:
    """Estimate whether one daylight hour is usable for bee flight."""
    temperature, rain = hour.get("temperature"), hour.get("rain_mm")
    temperature_score = (
        _band(temperature, 7, 14, 30, 36) if temperature is not None else 50
    )
    dry_score = max(0, 100 - 70 * max(0, rain or 0))
    wind_score = min(
        _falling(hour.get("wind_kmh"), 14, 35), _falling(hour.get("gust_kmh"), 25, 55)
    )
    light_score = min(100, max(0, (hour.get("radiation_wm2") or 0) / 250 * 100))
    return (
        0.3 * temperature_score
        + 0.3 * dry_score
        + 0.25 * wind_score
        + 0.15 * light_score
    )


def _band(
    value: float,
    outer_low: float,
    ideal_low: float,
    ideal_high: float,
    outer_high: float,
) -> float:
    if ideal_low <= value <= ideal_high:
        return 100
    if value <= outer_low or value >= outer_high:
        return 0
    if value < ideal_low:
        return 100 * (value - outer_low) / (ideal_low - outer_low)
    return 100 * (outer_high - value) / (outer_high - ideal_high)


def _falling(value: float | None, ideal_max: float, outer_max: float) -> float:
    if value is None or value <= ideal_max:
        return 100
    if value >= outer_max:
        return 0
    return 100 * (outer_max - value) / (outer_max - ideal_max)


def _float_or_none(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _average(values) -> float | None:
    present = [value for value in values if value is not None]
    return round(mean(present), 1) if present else None
