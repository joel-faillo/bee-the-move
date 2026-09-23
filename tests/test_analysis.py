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


def test_elevation_filter_is_explicit_and_bounded():
    assert _matches_elevation(450, "Below 600 m")
    assert not _matches_elevation(700, "Below 600 m")
    assert _matches_elevation(600, "600–1,000 m")
    assert _matches_elevation(1000, "600–1,000 m")
    assert _matches_elevation(1200, "Above 1,000 m")
    assert not _matches_elevation(None, "Above 1,000 m")
