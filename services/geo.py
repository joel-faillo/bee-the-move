"""GeoAdmin place search, terrain height, canton lookup and distance maths.

AI-assisted code generation and revision: OpenAI Codex (OpenAI, n.d.-b).
See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from __future__ import annotations

import html
import math
import re

from services.http import HttpClient

SEARCH_URL = "https://api3.geo.admin.ch/rest/services/ech/SearchServer"
HEIGHT_URL = "https://api3.geo.admin.ch/rest/services/height"
IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify"
CANTON_LAYER = "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill"
# A hive origin must be a concrete municipality/place or postcode. District
# and canton centroids are too broad and created ambiguous duplicate labels.
PLACE_ORIGINS = {"zipcode", "gg25"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def wgs84_to_lv95(latitude: float, longitude: float) -> tuple[float, float]:
    """Convert WGS84 to LV95 with swisstopo's official approximation."""
    lat = (latitude * 3600 - 169_028.66) / 10_000
    lon = (longitude * 3600 - 26_782.5) / 10_000
    easting = (
        2_600_072.37
        + 211_455.93 * lon
        - 10_938.51 * lon * lat
        - 0.36 * lon * lat**2
        - 44.54 * lon**3
    )
    northing = (
        1_200_147.07
        + 308_807.95 * lat
        + 3_745.25 * lon**2
        + 76.63 * lat**2
        - 194.56 * lon**2 * lat
        + 119.79 * lat**3
    )
    return easting, northing


class GeoAdminService:
    """Resolve Swiss places/CAPs and retrieve official point elevation."""

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def geocode(self, query: str) -> dict:
        results = self._search(query, limit=20)
        if not results:
            raise ValueError(f"Località non trovata: {query}")
        # The SearchServer also returns buildings and parcels. Administrative
        # places and postcodes are the meaningful origins for this application.
        preferred = [
            item
            for item in results
            if item.get("attrs", {}).get("origin") in PLACE_ORIGINS
        ]
        attrs = (preferred or results)[0].get("attrs", {})
        label = re.sub(r"<[^>]+>", "", attrs.get("label", query))
        return {
            "name": html.unescape(label),
            "lat": float(attrs["lat"]),
            "lon": float(attrs["lon"]),
        }

    def suggest(self, query: str, limit: int = 7) -> list[dict]:
        """Return clean autocomplete choices limited to places and postcodes."""
        suggestions = []
        seen = set()
        for item in self._search(query, limit=30):
            attrs = item.get("attrs", {})
            origin = attrs.get("origin")
            if origin not in PLACE_ORIGINS:
                continue
            label = html.unescape(
                re.sub(r"<[^>]+>", "", attrs.get("label", ""))
            ).strip()
            key = (origin, label.casefold())
            if not label or key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    "label": label,
                    "search_text": label,
                    "kind": "Postal code (CAP)" if origin == "zipcode" else "Place",
                    "postal_code": label.split(" - ", 1)[0]
                    if origin == "zipcode"
                    else "",
                    "lat": float(attrs["lat"]),
                    "lon": float(attrs["lon"]),
                }
            )
            if len(suggestions) >= limit:
                break
        return suggestions

    def _search(self, query: str, limit: int) -> list[dict]:
        data = self.http.get_json(
            SEARCH_URL,
            params={
                "searchText": query,
                "type": "locations",
                "origins": ",".join(sorted(PLACE_ORIGINS)),
                "sr": 4326,
                "limit": limit,
            },
            cache=False,
        )
        return data.get("results", [])

    def height(self, easting: float, northing: float) -> float | None:
        """Return terrain height in metres; this is context, not score input."""
        try:
            data = self.http.get_json(
                HEIGHT_URL,
                params={"easting": easting, "northing": northing, "sr": 2056},
            )
            return round(float(data["height"]), 1)
        except (KeyError, TypeError, ValueError):
            return None

    def canton(self, lat: float, lon: float) -> dict | None:
        """Return the official canton containing a WGS84 point.

        This is used only to route users to the competent cantonal veterinary
        office. It does not infer whether a hive move has been authorised.
        """
        data = self.http.get_json(
            IDENTIFY_URL,
            params={
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "sr": 4326,
                "layers": f"all:{CANTON_LAYER}",
                "returnGeometry": "false",
                "tolerance": 0,
            },
        )
        results = data.get("results", [])
        if not results:
            return None
        attrs = results[0].get("attributes", {})
        code = str(attrs.get("ak", "")).upper()
        return {"code": code, "name": attrs.get("name") or code}
