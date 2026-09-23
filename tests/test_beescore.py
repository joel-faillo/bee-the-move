from beescore import (
    calculate,
    continuity_score,
    distance_score,
    forage_score,
    weather_score,
)
from services.geo import haversine_km
from services.landscape import FORAGE_CATEGORIES, _forage_value, _lv95_to_wgs84


def test_haversine_st_gallen_to_appenzell_is_reasonable():
    distance = haversine_km(47.4245, 9.3767, 47.331, 9.409)
    assert 10 < distance < 12


def test_weather_rewards_dry_mild_days():
    good = weather_score([{"flight_score": 91}])
    poor = weather_score([{"flight_score": 12}])
    assert good > poor


def test_distance_score_uses_selected_radius():
    assert distance_score(0, 50) == 100
    assert distance_score(50, 50) == 0


def test_beescore_is_weighted_and_bounded():
    result = calculate(forage=80, flight_weather=70, continuity=60, logistics=90)
    assert result["score"] == 75
    assert set(result["components"]) == {
        "forage",
        "flight_weather",
        "continuity",
        "logistics",
    }


def test_forage_combines_current_bloom_and_mapped_resources():
    assert forage_score(80, 40) == 66


def test_continuity_penalises_unstable_flowering():
    stable = continuity_score([{"score": 70}] * 7, 60)
    unstable = continuity_score(
        [{"score": value} for value in [10, 90, 10, 90, 10, 90, 10]], 60
    )
    assert stable > unstable


def test_landscape_values_real_forage_above_cereals():
    orchard, _ = _forage_value("Hochstamm-Feldobstbäume")
    meadow, _ = _forage_value("Extensiv genutzte Wiesen")
    wheat, _ = _forage_value("Winterweizen")
    assert orchard > meadow > wheat


def test_every_search_filter_is_a_real_landscape_category():
    assert "Meadows" in FORAGE_CATEGORIES
    assert "Pastures" in FORAGE_CATEGORIES
    assert "Low-forage arable crops" in FORAGE_CATEGORIES


def test_lv95_map_points_convert_back_near_st_gallen():
    lat, lon = _lv95_to_wgs84(2_746_301, 1_255_286)
    assert abs(lat - 47.4321) < 0.001
    assert abs(lon - 9.3780) < 0.001
