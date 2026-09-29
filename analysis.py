"""Coordinate external data sources and build comparable candidate results.

Service modules fetch and normalise one source each; ``beescore.py`` contains
the pure scoring rules. This separation keeps every score component inspectable
and testable.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from beescore import (
    best_period,
    calculate,
    continuity_score,
    distance_score,
    forage_score,
    weather_score,
)
from services.geo import GeoAdminService
from services.landscape import LandscapeService
from services.meteoswiss import MeteoSwissForecastService
from services.phenology import PhenologyService
from services.pollen import PollenService
from services.routing import RoutingService


class BeeMoveAnalysis:
    """Compare MeteoSwiss forecast points around a searched Swiss origin."""

    def __init__(
        self,
        geo: GeoAdminService,
        forecast: MeteoSwissForecastService,
        phenology: PhenologyService,
        landscape: LandscapeService,
        pollen: PollenService,
        routing: RoutingService,
        flowering_model=None,
        max_candidates: int = 12,
    ) -> None:
        self.geo = geo
        self.forecast = forecast
        self.phenology = phenology
        self.landscape = landscape
        self.pollen = pollen
        self.routing = routing
        self.flowering_model = flowering_model
        self.max_candidates = max_candidates

    def run(
        self,
        location: str | dict,
        radius_km: float,
        forage_preference: str | None = None,
        elevation_preference: str = "Any elevation",
    ) -> dict:
        """Run the analysis and always retain the searched origin area."""
        # The autocomplete already resolves one exact GeoAdmin result. Reuse
        # those coordinates so an ambiguous label is not searched and ranked
        # a second time (for example Lausanne versus Belmont-sur-Lausanne).
        if isinstance(location, dict):
            origin = {
                "name": location.get("label") or location.get("name"),
                "lat": float(location["lat"]),
                "lon": float(location["lon"]),
            }
            if location.get("postal_code"):
                origin["postal_code"] = location["postal_code"]
        else:
            origin = self.geo.geocode(location)
        points = self.forecast.candidates(
            origin["lat"], origin["lon"], radius_km, self.max_candidates
        )
        if not points:
            raise ValueError(
                "Nessuna località MeteoSwiss trovata nel raggio selezionato"
            )

        forecasts, forecast_meta = self.forecast.forecasts(points)
        origin_point = min(points, key=lambda point: point.distance_km)
        pollen = self._safe(
            lambda: self.pollen.latest_near(origin["lat"], origin["lon"]),
            {"available": False},
        )
        phenology_station = self._safe(
            lambda: self.phenology.nearest_station(origin["lat"], origin["lon"]),
            None,
        )

        def enrich(point):
            # Every candidate receives identical inputs. Optional sources fail
            # independently instead of being replaced with fabricated values.
            is_origin_area = point.key == origin_point.key
            days = forecasts.get(point.key, [])
            dates = [day["date"] for day in days[:7]]
            height = self._safe(
                lambda: self.geo.height(point.easting, point.northing), None
            )
            height_source = "geoadmin"
            if height is None:
                height = point.metadata_height
                height_source = "meteoswiss_metadata"
            # The trained project model is the primary seasonal signal. Live
            # station observations remain an explicit fallback if the model
            # artifact has not yet been built or cannot be loaded.
            flowering = (
                self._safe(
                    lambda: self.flowering_model.predict_signal(
                        point.lat, point.lon, height, dates
                    ),
                    {"available": False, "daily": [], "score": 0},
                )
                if self.flowering_model
                else {"available": False, "daily": [], "score": 0}
            )
            if not flowering.get("available"):
                flowering = self._safe(
                    lambda: self.phenology.flowering_forecast(
                        point.lat, point.lon, dates
                    ),
                    {"available": False, "daily": [], "score": 0},
                )
            landscape = self._safe(
                lambda: self.landscape.analyse(
                    point.lat,
                    point.lon,
                    point.easting,
                    point.northing,
                    forage_preference,
                ),
                {
                    "available": False,
                    "score": 0,
                    "diversity_score": 0,
                    "top_resources": [],
                },
            )
            weather = weather_score(days)
            forage = forage_score(flowering.get("score", 0), landscape.get("score", 0))
            continuity = continuity_score(
                flowering.get("daily", []), landscape.get("diversity_score", 0)
            )
            # The nearest MeteoSwiss forecast point is only a measurement
            # proxy for the searched place. The place itself is, correctly,
            # zero kilometres from the origin.
            display_distance = 0.0 if is_origin_area else point.distance_km
            logistics = distance_score(display_distance, radius_km)
            score = calculate(forage, weather, continuity, logistics)
            return {
                "name": origin["name"] if is_origin_area else point.name,
                "postal_code": (
                    origin.get("postal_code") or point.postal_code
                    if is_origin_area else point.postal_code
                ),
                "lat": origin["lat"] if is_origin_area else point.lat,
                "lon": origin["lon"] if is_origin_area else point.lon,
                "distance_km": display_distance,
                "is_origin_area": is_origin_area,
                "forecast_reference": {
                    "name": point.name,
                    "distance_km": point.distance_km,
                },
                "route": None,
                "height_m": height,
                "height_source": height_source,
                "weather": {"score": weather, "days": days[:7]},
                "flowering": flowering,
                "landscape": landscape,
                "best_period": best_period(days, flowering.get("daily", [])),
                **score,
            }

        with ThreadPoolExecutor(max_workers=min(8, len(points) + 1)) as executor:
            # One compact set of centroids powers the useful Meadows/Pastures
            # map filters without sending hundreds of heavy polygons.
            forage_map_future = executor.submit(
                self.landscape.map_points, origin["lat"], origin["lon"]
            )
            candidates = list(executor.map(enrich, points))
            forage_map = self._safe(forage_map_future.result, [])

        candidates.sort(key=lambda item: item["score"], reverse=True)
        if self.routing.enabled:
            route_targets = [
                candidate
                for candidate in candidates
                if not candidate["is_origin_area"]
            ]
            for candidate in route_targets:
                route = self._safe(
                    lambda candidate=candidate: self.routing.route(
                        (origin["lat"], origin["lon"]),
                        (candidate["lat"], candidate["lon"]),
                    ),
                    None,
                )
                if route:
                    candidate["route"] = route
                    candidate["components"]["logistics"] = distance_score(
                        route["distance_km"], radius_km
                    )
                    candidate["score"] = calculate(
                        candidate["components"]["forage"],
                        candidate["components"]["flight_weather"],
                        candidate["components"]["continuity"],
                        candidate["components"]["logistics"],
                    )["score"]
            candidates.sort(key=lambda item: item["score"], reverse=True)

        # Elevation is an eligibility preference, not a hidden score bonus.
        # The searched place remains visible as a reference even if it falls
        # outside the selected band.
        eligible = [
            candidate
            for candidate in candidates
            if _matches_elevation(candidate["height_m"], elevation_preference)
        ]
        ranked = eligible[:3]
        origin_candidate = next(
            candidate for candidate in candidates if candidate["is_origin_area"]
        )
        if origin_candidate not in ranked:
            ranked.append(origin_candidate)

        phenology_available = any(
            candidate["flowering"].get("available") for candidate in candidates
        )
        landscape_available = any(
            candidate["landscape"].get("available") for candidate in candidates
        )

        return {
            "origin": origin,
            "radius_km": radius_km,
            "forage_preference": forage_preference,
            "elevation_preference": elevation_preference,
            "results": ranked,
            "pollen": pollen,
            "phenology_station": phenology_station,
            "forage_map": forage_map,
            "score_method": {
                "forage": 45,
                "flight_weather": 30,
                "continuity": 15,
                "logistics": 10,
            },
            "sources": {
                "geoadmin_search": True,
                "geoadmin_height": any(
                    candidate["height_m"] is not None
                    and candidate["height_source"] == "geoadmin"
                    for candidate in candidates
                ),
                "meteoswiss_forecast": forecast_meta,
                "meteoswiss_phenology": phenology_available,
                "trained_flowering_model": self.flowering_model is not None,
                "meteoswiss_pollen": pollen.get("available", False),
                "agricultural_land_use": landscape_available,
                "swisstopo_vector_tiles": True,
                "openrouteservice": {
                    "configured": self.routing.enabled,
                    "successful_routes": sum(
                        bool(candidate.get("route")) for candidate in candidates
                    ),
                },
            },
        }

    @staticmethod
    def _safe(operation, fallback):
        try:
            return operation()
        except Exception:
            return fallback


def _matches_elevation(height_m: float | None, preference: str) -> bool:
    """Apply the visible search filter without changing the BeeScore."""
    if preference == "Any elevation":
        return True
    if height_m is None:
        return False
    if preference == "Below 600 m":
        return height_m < 600
    if preference == "600–1,000 m":
        return 600 <= height_m <= 1000
    if preference == "Above 1,000 m":
        return height_m > 1000
    return True
