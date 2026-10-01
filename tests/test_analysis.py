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


def test_searched_area_evidence_uses_the_exact_selected_coordinates():
    class RecordingLandscape(StubLandscape):
        def __init__(self):
            self.coordinates = None

        def analyse(self, lat, lon, *_args):
            self.coordinates = lat, lon
            return super().analyse(lat, lon, *_args)

    landscape = RecordingLandscape()
    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=StubForecast(),
        phenology=StubPhenology(),
        landscape=landscape,
        pollen=StubPollen(),
        routing=StubRouting(),
    )
    selected = {"label": "Exact place", "lat": 47.4, "lon": 9.3}

    analysis.run(selected, 10)

    assert landscape.coordinates == (47.4, 9.3)


def test_selected_postcode_reaches_the_searched_destination():
    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=StubForecast(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    result = analysis.run(
        {
            "label": "9000 - St. Gallen",
            "postal_code": "9000",
            "lat": 47.4245,
            "lon": 9.3767,
        },
        10,
        colony_count=12,
    )

    assert result["results"][0]["postal_code"] == "9000"
    assert result["colony_count"] == 12


def test_missing_core_evidence_is_not_presented_as_a_comparable_score():
    class MissingLandscape(StubLandscape):
        def analyse(self, *_args):
            return {
                "available": False,
                "score": 0,
                "diversity_score": 0,
                "top_resources": [],
            }

    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=StubForecast(),
        phenology=StubPhenology(),
        landscape=MissingLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    candidate = analysis.run("St. Gallen", 10)["results"][0]
    assert candidate["score"] is None
    assert not candidate["ranking_ready"]


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

    with pytest.raises(ValueError, match="No MeteoSwiss location"):
        analysis.run("St. Gallen", 10)


def test_weather_failure_keeps_historical_planning_available():
    class UnavailableWeather(StubForecast):
        def forecasts(self, _points):
            raise ConnectionError("temporary outage")

    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=UnavailableWeather(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    result = analysis.run(
        "St. Gallen",
        10,
        analysis_date="2027-04-01",
        planning_end_date="2027-04-28",
    )

    assert result["sources"]["meteoswiss_forecast"] == {"available": False}
    assert result["results"][0]["weather"]["days"] == []
    assert result["results"][0]["flowering"]["available"]


def test_selected_analysis_date_filters_the_available_forecast():
    class NineDayForecast(StubForecast):
        def forecasts(self, _points):
            return {
                self.point.key: [
                    {
                        "date": f"2026-09-{day:02d}",
                        "flight_score": 70,
                        "flight_hours": 8,
                    }
                    for day in range(18, 27)
                ]
            }, {"updated": "2026-09-18T10:00:00Z"}

    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=NineDayForecast(),
        phenology=StubPhenology(),
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    result = analysis.run("St. Gallen", 50, analysis_date="2026-09-22")

    assert result["analysis_date"] == "2026-09-22"
    assert result["forecast_window_end"] == "2026-09-26"
    assert result["forecast_lead_days"] == 4
    assert [day["date"] for day in result["results"][0]["weather"]["days"]] == [
        "2026-09-22",
        "2026-09-23",
        "2026-09-24",
        "2026-09-25",
        "2026-09-26",
    ]

    future = analysis.run(
        "St. Gallen",
        50,
        analysis_date="2026-09-27",
        planning_end_date="2026-10-24",
    )
    assert future["forecast_lead_days"] is None
    assert future["planning_days"] == 28
    assert future["results"][0]["weather"]["days"] == []
    assert not future["results"][0]["forecast_confirmed"]


def test_planned_stay_drives_the_complete_flowering_signal():
    class RecordingPhenology(StubPhenology):
        def __init__(self):
            self.dates = []

        def flowering_forecast(self, _lat, _lon, dates):
            self.dates = dates
            return super().flowering_forecast(_lat, _lon, dates)

    phenology = RecordingPhenology()
    analysis = BeeMoveAnalysis(
        geo=StubGeo(),
        forecast=StubForecast(),
        phenology=phenology,
        landscape=StubLandscape(),
        pollen=StubPollen(),
        routing=StubRouting(),
    )

    result = analysis.run(
        "St. Gallen",
        10,
        analysis_date="2026-09-18",
        planning_end_date="2026-10-15",
    )

    assert len(phenology.dates) == 28
    assert phenology.dates[0] == "2026-09-18"
    assert phenology.dates[-1] == "2026-10-15"
    assert len(result["results"][0]["flowering"]["daily"]) == 28


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
