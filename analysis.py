"""Coordinate external data sources and build comparable candidate results.

Service modules fetch and normalise one source each; ``beescore.py`` contains
the pure scoring rules. This separation keeps every score component inspectable
and testable.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from beescore import (
    best_period,
    calculate,
    continuity_score,
    distance_score,
    forage_score,
    weather_score,
)
from services.geo import GeoAdminService, wgs84_to_lv95
from services.climate_normals import ClimateNormalsService
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
        climate: ClimateNormalsService | None = None,
        flowering_model=None,
        max_candidates: int = 12,
    ) -> None:
        self.geo = geo
        self.forecast = forecast
        self.phenology = phenology
        self.landscape = landscape
        self.pollen = pollen
        self.routing = routing
        self.climate = climate
        self.flowering_model = flowering_model
        self.max_candidates = max_candidates

    def run(
        self,
        location: str | dict,
        radius_km: float,
        forage_preference: str | None = None,
        elevation_preference: str = "Any elevation",
        analysis_date: str | None = None,
        planning_end_date: str | None = None,
        colony_count: int = 1,
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
                "No MeteoSwiss location was found within the selected radius"
            )

        forecasts, forecast_meta = self._safe(
            lambda: self.forecast.forecasts(points),
            ({}, {"available": False}),
        )
        forecast_meta = {"available": bool(forecasts), **forecast_meta}
        forecast_dates = sorted(
            {
                day["date"]
                for point_days in forecasts.values()
                for day in point_days
            }
        )
        today = date.today()
        selected = date.fromisoformat(analysis_date) if analysis_date else today
        planned_end = (
            date.fromisoformat(planning_end_date)
            if planning_end_date
            else selected + timedelta(days=27)
        )
        if planned_end < selected:
            raise ValueError("The planned end date must not precede the arrival date")
        if (planned_end - selected).days > 365:
            raise ValueError("The planning period cannot exceed one year")
        selected_date = selected.isoformat()
        planning_end_date = planned_end.isoformat()
        planning_dates = [
            (selected + timedelta(days=offset)).isoformat()
            for offset in range((planned_end - selected).days + 1)
        ]
        forecast_lead_days = (
            (selected - date.fromisoformat(forecast_dates[0])).days
            if forecast_dates and selected_date in forecast_dates
            else None
        )
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
            evaluation_lat = origin["lat"] if is_origin_area else point.lat
            evaluation_lon = origin["lon"] if is_origin_area else point.lon
            evaluation_easting, evaluation_northing = (
                wgs84_to_lv95(evaluation_lat, evaluation_lon)
                if is_origin_area
                else (point.easting, point.northing)
            )
            days = [
                day
                for day in forecasts.get(point.key, [])
                if selected_date <= day["date"] <= planning_end_date
            ][:7]
            height = self._safe(
                lambda: self.geo.height(evaluation_easting, evaluation_northing), None
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
                        evaluation_lat,
                        evaluation_lon,
                        height,
                        planning_dates,
                        forage_preference,
                    ),
                    {"available": False, "daily": [], "score": 0},
                )
                if self.flowering_model
                else {"available": False, "daily": [], "score": 0}
            )
            if not flowering.get("available"):
                flowering = self._safe(
                    lambda: self.phenology.flowering_forecast(
                        evaluation_lat, evaluation_lon, planning_dates
                    ),
                    {"available": False, "daily": [], "score": 0},
                )
            landscape = self._safe(
                lambda: self.landscape.analyse(
                    evaluation_lat,
                    evaluation_lon,
                    evaluation_easting,
                    evaluation_northing,
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
            weather_component = weather if days else None
            forage = forage_score(flowering.get("score", 0), landscape.get("score", 0))
            continuity = continuity_score(
                flowering.get("daily", []), landscape.get("diversity_score", 0)
            )
            # The nearest MeteoSwiss forecast point is only a measurement
            # proxy for the searched place. The place itself is, correctly,
            # zero kilometres from the origin.
            display_distance = 0.0 if is_origin_area else point.distance_km
            logistics = distance_score(display_distance)
            score = calculate(forage, weather_component, continuity, logistics)
            ranking_ready = bool(
                flowering.get("available") and landscape.get("available")
            )
            if not ranking_ready:
                score["score"] = None
            climate = (
                self._safe(
                    lambda: self.climate.summary(
                        evaluation_easting,
                        evaluation_northing,
                        selected_date,
                        planning_end_date,
                    ),
                    {"available": False},
                )
                if self.climate
                else {"available": False}
            )
            return {
                "name": origin["name"] if is_origin_area else point.name,
                "postal_code": (
                    origin.get("postal_code") or point.postal_code
                    if is_origin_area else point.postal_code
                ),
                "lat": evaluation_lat,
                "lon": evaluation_lon,
                "distance_km": display_distance,
                "is_origin_area": is_origin_area,
                "forecast_reference": {
                    "name": point.name,
                    "distance_km": point.distance_km,
                },
                "route": None,
                "height_m": height,
                "height_source": height_source,
                "weather": {"score": weather_component, "days": days[:7]},
                "flowering": flowering,
                "landscape": landscape,
                "climate_normals": climate,
                "best_period": best_period(days, flowering.get("daily", [])),
                "ranking_ready": ranking_ready,
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

        candidates.sort(key=_ranking_key, reverse=True)
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
                        route["distance_km"]
                    )
                    candidate.update(
                        calculate(
                            candidate["components"]["forage"],
                            candidate["components"]["flight_weather"],
                            candidate["components"]["continuity"],
                            candidate["components"]["logistics"],
                        )
                    )
                    if not candidate["ranking_ready"]:
                        candidate["score"] = None
            candidates.sort(key=_ranking_key, reverse=True)

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
            "analysis_date": selected_date,
            "planning_end_date": planning_end_date,
            "planning_days": len(planning_dates),
            "colony_count": max(1, int(colony_count)),
            "forecast_window_end": forecast_dates[-1] if forecast_dates else None,
            "forecast_lead_days": forecast_lead_days,
            "forage_preference": forage_preference,
            "elevation_preference": elevation_preference,
            "results": ranked,
            "pollen": pollen,
            "phenology_station": phenology_station,
            "forage_map": forage_map,
            "score_method": {
                "forage": 70,
                "flight_weather": 0,
                "continuity": 20,
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
                "meteoswiss_climate_normals": any(
                    candidate["climate_normals"].get("available")
                    for candidate in candidates
                ),
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
    """Apply the visible filter without changing the regional index."""
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


def _ranking_key(candidate: dict) -> tuple[bool, float]:
    """Complete evidence always ranks ahead of a partial, unscored result."""
    score = candidate.get("score")
    return score is not None, float(score) if score is not None else -1.0
