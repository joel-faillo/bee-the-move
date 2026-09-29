from dataclasses import replace

import pytest

from services.meteoswiss import ForecastPoint

from analysis import BeeMoveAnalysis, _matches_elevation


class StubGeo:
    def geocode(self, _location):
        return {"name": "St. Gallen", "lat": 47.4245, "lon": 9.3767}

    def height(self, _easting, _northing):
        return 675


class StubForecast:
    point = ForecastPoint(
        point_id="origin-grid",
        point_type_id="2",
        name="St. Gallen forecast point",
        postal_code="9000",
        lat=47.428,
        lon=9.38,
        easting=2746000,
        northing=1255000,
        metadata_height=670,
        distance_km=0.5,
    )

    def candidates(self, *_args):
        return [self.point]

    def forecasts(self, _points):
        return {
            self.point.key: [
                {"date": "2026-09-18", "flight_score": 70, "flight_hours": 8}
            ]
        }, {"updated": "2026-09-18T10:00:00Z"}


class StubPhenology:
    def flowering_forecast(self, _lat, _lon, dates):
        return {
            "available": True,
            "score": 60,
            "daily": [{"date": date, "score": 60} for date in dates],
        }


class StubLandscape:
    def analyse(self, *_args):
        return {
            "available": True,
            "score": 50,
            "diversity_score": 50,
            "top_resources": [],
        }

    def map_points(self, *_args):
        return []


class StubPollen:
    def latest_near(self, *_args):
        return {"available": False}


class StubRouting:
    enabled = False


def test_searched_place_is_zero_km_but_keeps_forecast_reference_distance():
    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=StubForecast(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
        max_candidates=3,
    )

    result = analysis.run("St. Gallen", 50)["results"][0]

    assert result["name"] == "St. Gallen"
    assert result["distance_km"] == 0
    assert result["components"]["logistics"] == 100
    assert result["forecast_reference"]["distance_km"] == 0.5
    assert result["height_source"] == "geoadmin"


def test_selected_autocomplete_coordinates_are_not_geocoded_again():
    class GeoThatMustNotSearch(StubGeo):
        def geocode(self, _location):
            raise AssertionError("The selected GeoAdmin result must be reused")

    analysis = BeeMoveAnalysis(
        geo=GeoThatMustNotSearch(),
        forecast=StubForecast(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
        max_candidates=3,
    )
    selected = {
        "label": "Lausanne (VD)",
        "lat": 46.52865,
        "lon": 6.63852,
    }

    result = analysis.run(selected, 50)

    assert result["origin"] == {
        "name": "Lausanne (VD)",
        "lat": 46.52865,
        "lon": 6.63852,
    }


def test_elevation_filter_is_explicit_and_bounded():
    assert _matches_elevation(450, "Below 600 m")
    assert not _matches_elevation(700, "Below 600 m")
    assert _matches_elevation(600, "600–1,000 m")
    assert _matches_elevation(1000, "600–1,000 m")
    assert _matches_elevation(1200, "Above 1,000 m")
    assert not _matches_elevation(None, "Above 1,000 m")


def test_no_forecast_candidate_produces_a_clear_error():
    class EmptyForecast(StubForecast):
        def candidates(self, *_args):
            return []

    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=EmptyForecast(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    with pytest.raises(ValueError, match="Nessuna località MeteoSwiss"):
        analysis.run("St. Gallen", 10)


def test_meteoswiss_height_is_used_only_when_geoadmin_height_is_unavailable():
    class GeoWithoutHeight(StubGeo):
        def height(self, _easting, _northing):
            return None

    analysis = BeeMoveAnalysis(
        geo=GeoWithoutHeight(),
        forecast=StubForecast(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    result = analysis.run("St. Gallen", 50)["results"][0]

    assert result["height_m"] == StubForecast.point.metadata_height
    assert result["height_source"] == "meteoswiss_metadata"


def test_road_distance_is_computed_for_every_alternative_before_final_ranking():
    class ManyForecasts(StubForecast):
        points = [
            replace(
                StubForecast.point,
                point_id=f"point-{index}",
                name=f"Place {index}",
                lat=47.428 + index / 100,
                distance_km=float(index),
            )
            for index in range(8)
        ]

        def candidates(self, *_args):
            return self.points

        def forecasts(self, points):
            return {
                point.key: [
                    {"date": "2026-09-29", "flight_score": 70, "flight_hours": 8}
                ]
                for point in points
            }, {"updated": "2026-09-29T00:00:00Z"}

    class RecordingRouting:
        enabled = True

        def __init__(self):
            self.destinations = []

        def route(self, _origin, destination):
            self.destinations.append(destination)
            return {"distance_km": 12.0, "duration_minutes": 20}

    routing = RecordingRouting()
    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=ManyForecasts(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=routing,
        max_candidates=8,
    )

    result = analysis.run("St. Gallen", 50)

    assert len(routing.destinations) == 7
    assert all(
        candidate["route"] is not None
        for candidate in result["results"]
        if not candidate["is_origin_area"]
    )
    assert result["sources"]["openrouteservice"] == {
        "configured": True,
        "successful_routes": 7,
    }
