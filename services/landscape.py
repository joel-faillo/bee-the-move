"""Agricultural forage context from the harmonised Swiss OGC API.

Declared feature area is weighted by an explicit forage category and by
distance in 1, 2 and 3 km rings. The source maps agricultural use, not nectar,
flowering, pesticide exposure or bee access. Category values and normalisation
thresholds are therefore transparent prototype assumptions, not official
nectar-yield coefficients.

AI-assisted code generation and revision: OpenAI Codex (OpenAI, n.d.-b).
See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from __future__ import annotations

import math
from collections import defaultdict

from shapely import make_valid
from shapely.geometry import Point, shape

from services.geo import wgs84_to_lv95
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
        reference_years = _reference_years(features)
        resources = defaultdict(float)
        weighted_square_metres = mapped_square_metres = 0.0
        categories = set()
        valid_feature_count = 0
        circles = [
            Point(easting, northing).buffer(radius) for radius in (1000, 2000, 3000)
        ]
        for feature in features:
            props = feature.get("properties", {})
            if not _is_active_feature(props):
                continue
            area = _number(props.get("flaeche_m2"))
            if area <= 0:
                continue
            name = str(props.get("nutzung", "Sconosciuto"))
            value, category = _forage_value(name)
            geometry = _area_geometry(feature)
            if geometry is None:
                continue
            within = [geometry.intersection(circle).area for circle in circles]
            if within[2] <= 0:
                continue
            valid_feature_count += 1
            # Multipart records may include distant fields. Allocate the declared
            # crop area by the geometric share actually inside each distance ring.
            scale = area / geometry.area
            weighted_area = (
                within[0]
                + 0.6 * (within[1] - within[0])
                + 0.25 * (within[2] - within[1])
            )
            contribution = scale * weighted_area * value
            weighted_square_metres += contribution
            mapped_square_metres += scale * within[2]
            resources[category] += contribution
            if value >= 0.45:
                categories.add(category)

        selected_square_metres = resources.get(preferred_category, 0.0)
        # A chosen forage type becomes the abundance target. The lower
        # denominator reflects that one category naturally covers less area
        # than the complete agricultural mosaic. Both saturation thresholds
        # are project heuristics: the public dataset provides area and land-use
        # labels, but no official conversion from square metres to bee forage.
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
            # An incomplete OGC response cannot support a comparable regional rank.
            "available": valid_feature_count > 0 and number_matched <= len(features),
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
            "reference_year": max(reference_years, default=None),
            "reference_years": reference_years,
            "feature_count": len(features),
            "valid_feature_count": valid_feature_count,
            "truncated": number_matched > len(features),
            "method": "superfici agricole ponderate per valore mellifero e distanza in anelli di 1, 2 e 3 km; il filtro opzionale concentra la componente risorse sulla categoria scelta",
        }

    def map_points(self, lat: float, lon: float) -> list[dict]:
        """Return representative crop points inside the 3 km forage area.

        A point is guaranteed to lie on the locally clipped parcel geometry.
        Multipart records must not appear at an average position between fields.
        """
        features, _number_matched = self._features(lat, lon)
        easting, northing = wgs84_to_lv95(lat, lon)
        circle = Point(easting, northing).buffer(3000)
        points = []
        for feature in features:
            props = feature.get("properties", {})
            if not _is_active_feature(props):
                continue
            name = str(props.get("nutzung", ""))
            _value, category = _forage_value(name)
            geometry = _area_geometry(feature)
            if geometry is None:
                continue
            clipped = geometry.intersection(circle)
            if clipped.area <= 0:
                continue
            point = clipped.representative_point()
            point_lat, point_lon = _lv95_to_wgs84(point.x, point.y)
            points.append(
                {
                    "lat": round(point_lat, 6),
                    "lon": round(point_lon, 6),
                    "category": category,
                    "name": name,
                    "year": props.get("bezugsjahr"),
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
                "bbox": f"{lon - longitude_delta},{lat - latitude_delta},{lon + longitude_delta},{lat + latitude_delta}",
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
    if "weide" in value or "sömmer" in value or "soemmer" in value:
        return 0.65, "Pastures"
    if "klee" in value or "luzerne" in value:
        return 0.65, "Clover and lucerne"
    if any(term in value for term in ("extensiv", "wenig intensiv", "wiese")):
        return 0.65, "Meadows"
    if any(term in value for term in LOW_VALUE):
        return 0.08, "Low-forage arable crops"
    return 0.25, "Other agricultural vegetation"


def _reference_years(features: list[dict]) -> list[int]:
    """Return every current reference year present in the mixed national feed."""
    return sorted(
        {
            year
            for feature in features
            if isinstance(
                (year := feature.get("properties", {}).get("bezugsjahr")), int
            )
        }
    )


def _is_active_feature(props: dict) -> bool:
    """Reject overlay and explicitly non-current parcel records.

    The national feed already exposes each provider's current publication, but
    reference years can differ inside one search window. Filtering on one
    global year would therefore discard valid neighbouring records.
    """
    if props.get("ist_ueberlagernd") is True:
        return False
    if props.get("ist_definitiv") is False:
        return False
    if props.get("nutzung_im_beitragsjahr") is False:
        return False
    return True


def _area_geometry(feature: dict):
    """Validate official Polygon/MultiPolygon shapes in projected LV95 metres."""
    raw = feature.get("geometry") or {}
    if raw.get("type") not in {"Polygon", "MultiPolygon"}:
        return None
    geometry = make_valid(shape(raw))
    return geometry if geometry.area > 0 else None


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
