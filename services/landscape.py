"""Agricultural forage context from the harmonised Swiss OGC API.

Declared feature area is weighted by an explicit forage category and by
distance in 1, 2 and 3 km rings. This is a prototype resource index, not an
official nectar-yield prediction.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

import math
from collections import defaultdict

from services.http import HttpClient

AGRICULTURAL_URL = "https://www.geodienste.ch/db/lwb_nutzungsflaechen_v3_0_0/deu/ogcapi/collections/nutzungsflaechen/items"
CRS2056 = "http://www.opengis.net/def/crs/EPSG/0/2056"
LOW_VALUE = ("mais", "weizen", "gerste", "getreide", "kartoff", "zuckerr")
FORAGE_CATEGORIES = (
    "Orchards and high-stem fruit trees",
    "Rapeseed",
    "Flower strips and biodiversity areas",
    "Flowering crops",
    "Meadows",
    "Pastures",
    "Clover and lucerne",
    "Other agricultural vegetation",
    "Low-forage arable crops",
)


class LandscapeService:
    """Summarise mapped forage in weighted 1, 2 and 3 km rings."""

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def analyse(
        self,
        lat: float,
        lon: float,
        easting: float,
        northing: float,
        preferred_category: str | None = None,
    ) -> dict:
        features, number_matched = self._features(lat, lon)
        years = [item.get("properties", {}).get("bezugsjahr") for item in features]
        current_year = max(
            (year for year in years if isinstance(year, int)), default=None
        )
        resources = defaultdict(float)
        weighted_square_metres = mapped_square_metres = 0.0
        categories = set()
        for feature in features:
            props = feature.get("properties", {})
            if current_year and props.get("bezugsjahr") != current_year:
                continue
            if props.get("ist_ueberlagernd"):
                continue
            area = _number(props.get("flaeche_m2"))
            if area <= 0:
                continue
            name = str(props.get("nutzung", "Sconosciuto"))
            value, category = _forage_value(name)
            x, y = _centroid(feature.get("geometry", {}).get("coordinates"))
            distance = math.hypot(x - easting, y - northing) if x is not None else 3000
            ring_weight = (
                1.0
                if distance <= 1000
                else 0.6 if distance <= 2000 else 0.25 if distance <= 3200 else 0
            )
            contribution = area * value * ring_weight
            weighted_square_metres += contribution
            mapped_square_metres += area
            resources[category] += contribution
            if value >= 0.45:
                categories.add(category)

        selected_square_metres = resources.get(preferred_category, 0.0)
        # A chosen forage type becomes the abundance target. The lower
        # denominator reflects that one category naturally covers less area
        # than the complete agricultural mosaic.
        availability = min(
            100,
            (
                selected_square_metres / 750_000
                if preferred_category
                else weighted_square_metres / 2_500_000
            )
            * 100,
        )
        diversity = min(100, len(categories) * 20)
        return {
            "available": True,
            "score": round(0.8 * availability + 0.2 * diversity, 1),
            "diversity_score": round(diversity, 1),
            "mapped_hectares": round(mapped_square_metres / 10_000, 1),
            "forage_hectares_equivalent": round(weighted_square_metres / 10_000, 1),
            "preferred_category": preferred_category,
            "preferred_hectares_equivalent": round(selected_square_metres / 10_000, 1),
            "top_resources": [
                name
                for name, _ in sorted(
                    resources.items(), key=lambda item: item[1], reverse=True
                )[:3]
            ],
            "reference_year": current_year,
            "feature_count": len(features),
            "truncated": number_matched > len(features),
            "method": "superfici agricole ponderate per valore mellifero e distanza in anelli di 1, 2 e 3 km; il filtro opzionale concentra la componente risorse sulla categoria scelta",
        }

    def map_points(self, lat: float, lon: float) -> list[dict]:
        """Return lightweight centroids for useful forage map filters.

        The source requires LV95 geometries. Only centroids are converted to
        WGS84, keeping the browser response small and the visualisation honest:
        these are mapped crop locations, not reconstructed field boundaries.
        """
        features, _number_matched = self._features(lat, lon)
        years = [item.get("properties", {}).get("bezugsjahr") for item in features]
        current_year = max(
            (year for year in years if isinstance(year, int)), default=None
        )
        points = []
        for feature in features:
            props = feature.get("properties", {})
            if current_year and props.get("bezugsjahr") != current_year:
                continue
            name = str(props.get("nutzung", ""))
            _value, category = _forage_value(name)
            easting, northing = _centroid(
                feature.get("geometry", {}).get("coordinates")
            )
            if easting is None:
                continue
            point_lat, point_lon = _lv95_to_wgs84(easting, northing)
            points.append(
                {
                    "lat": round(point_lat, 6),
                    "lon": round(point_lon, 6),
                    "category": category,
                    "name": name,
                    "year": current_year,
                }
            )
        return points

    def _features(self, lat: float, lon: float) -> tuple[list[dict], int]:
        """Read every OGC page inside the 3 km forage window.

        geodienste.ch caps one response at 1,000 features. Following its
        official ``next`` links prevents dense agricultural areas from being
        scored on only the first, arbitrary page.
        """
        latitude_delta = 3 / 110.574
        longitude_delta = 3 / (111.32 * math.cos(math.radians(lat)))
        page = self.http.get_json(
            AGRICULTURAL_URL,
            params={
                "f": "json",
                "bbox": f"{lon-longitude_delta},{lat-latitude_delta},{lon+longitude_delta},{lat+latitude_delta}",
                "crs": CRS2056,
                "limit": 1000,
            },
        )
        features = list(page.get("features", []))
        number_matched = int(page.get("numberMatched") or len(features))
        seen = set()
        while len(features) < number_matched:
            next_url = next(
                (
                    link.get("href")
                    for link in page.get("links", [])
                    if link.get("rel") == "next"
                ),
                None,
            )
            if not next_url or next_url in seen:
                break
            seen.add(next_url)
            page = self.http.get_json(next_url)
            features.extend(page.get("features", []))
        return features, number_matched


def _forage_value(name: str) -> tuple[float, str]:
    value = name.casefold()
    if "hochsta" in value or "obstan" in value:
        return 1.0, "Orchards and high-stem fruit trees"
    if "raps" in value:
        return 1.0, "Rapeseed"
    if any(
        term in value
        for term in ("blüh", "blueh", "buntbrache", "rotationsbrache", "hecke")
    ):
        return 1.0, "Flower strips and biodiversity areas"
    if "sonnenbl" in value or "buchweizen" in value:
        return 1.0, "Flowering crops"
    if any(term in value for term in ("extensiv", "wenig intensiv", "wiese")):
        return 0.65, "Meadows"
    if "weide" in value or "sömmer" in value or "soemmer" in value:
        return 0.65, "Pastures"
    if "klee" in value or "luzerne" in value:
        return 0.65, "Clover and lucerne"
    if any(term in value for term in LOW_VALUE):
        return 0.08, "Low-forage arable crops"
    return 0.25, "Other agricultural vegetation"


def _centroid(coordinates) -> tuple[float | None, float | None]:
    points = []

    def collect(value):
        if (
            isinstance(value, (list, tuple))
            and len(value) >= 2
            and all(isinstance(item, (int, float)) for item in value[:2])
        ):
            points.append((float(value[0]), float(value[1])))
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect(item)

    collect(coordinates)
    if not points:
        return None, None
    return sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(
        points
    )


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _lv95_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert LV95 to WGS84 with swisstopo's official approximation."""
    y = (easting - 2_600_000) / 1_000_000
    x = (northing - 1_200_000) / 1_000_000
    longitude_seconds = (
        2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x**2 - 0.0436 * y**3
    )
    latitude_seconds = (
        16.9023892
        + 3.238272 * x
        - 0.270978 * y**2
        - 0.002528 * x**2
        - 0.0447 * y**2 * x
        - 0.0140 * x**3
    )
    return latitude_seconds * 100 / 36, longitude_seconds * 100 / 36
