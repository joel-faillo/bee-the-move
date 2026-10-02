from beescore import (
    best_period,
    calculate,
    continuity_score,
    distance_score,
    forage_score,
    weather_score,
)
from services.geo import haversine_km
from services.landscape import FORAGE_CATEGORIES, _forage_value, _lv95_to_wgs84
import pytest


def test_haversine_st_gallen_to_appenzell_is_reasonable():
    distance = haversine_km(47.4245, 9.3767, 47.331, 9.409)
    assert 10 < distance < 12


def test_weather_rewards_dry_mild_days():
    good = weather_score([{"flight_score": 91}])
    poor = weather_score([{"flight_score": 12}])
    assert good > poor


def test_distance_score_uses_a_fixed_scale():
    assert distance_score(0) == 100
    assert distance_score(25) == 50
    assert distance_score(50) == 0


def test_beescore_is_weighted_and_bounded():
    result = calculate(forage=80, flight_weather=70, continuity=60, logistics=90)
    assert result["score"] == 75
    assert set(result["components"]) == {
        "forage",
        "flight_weather",
        "continuity",
        "logistics",
    }
    assert result["forecast_confirmed"]


def test_weather_is_context_and_does_not_change_regional_ranking():
    with_weather = calculate(forage=80, flight_weather=10, continuity=60, logistics=90)
    without_weather = calculate(forage=80, flight_weather=None, continuity=60, logistics=90)

    assert with_weather["score"] == without_weather["score"] == 75
    assert without_weather["components"]["flight_weather"] is None
    assert not without_weather["forecast_confirmed"]
    assert sum(without_weather["applied_weights"].values()) == pytest.approx(100)


def test_logistics_is_visible_but_does_not_change_biological_ranking():
    near = calculate(forage=70, flight_weather=80, continuity=60, logistics=100)
    far = calculate(forage=70, flight_weather=80, continuity=60, logistics=0)

    assert near["score"] == far["score"]
    assert near["components"]["logistics"] == 100
    assert far["components"]["logistics"] == 0


def test_forage_combines_current_bloom_and_mapped_resources():
    assert forage_score(80, 40) == 66


def test_continuity_penalises_unstable_flowering():
    stable = continuity_score([{"score": 70}] * 7, 60)
    unstable = continuity_score(
        [{"score": value} for value in [10, 90, 10, 90, 10, 90, 10]], 60
    )
    assert stable > unstable


def test_best_period_reports_the_available_window_length():
    weather = [
        {"date": f"2026-10-0{day}", "flight_score": score}
        for day, score in ((1, 20), (2, 80), (3, 90), (4, 70))
    ]
    flowering = [{"date": day["date"], "score": 60} for day in weather]

    assert best_period(weather, flowering) == {
        "from": "2026-10-02",
        "to": "2026-10-04",
        "days": 3,
    }


def test_landscape_values_real_forage_above_cereals():
    orchard, _ = _forage_value("Hochstamm-Feldobstbäume")
    meadow, _ = _forage_value("Extensiv genutzte Wiesen")
    wheat, _ = _forage_value("Winterweizen")
    assert orchard > meadow > wheat


@pytest.mark.parametrize(
    ("source_name", "category"),
    [
        ("Hochstamm-Feldobstbäume", "Orchards and high-stem fruit trees"),
        ("Raps", "Rapeseed"),
        ("Buntbrache", "Flower strips and biodiversity areas"),
        ("Sonnenblumen", "Flowering crops"),
        ("Extensiv genutzte Wiesen", "Meadows"),
        ("Dauerweide", "Pastures"),
        ("Luzerne", "Clover and lucerne"),
        ("Rebfläche", "Other agricultural vegetation"),
        ("Winterweizen", "Low-forage arable crops"),
    ],
)
def test_every_forage_filter_has_a_real_source_mapping(source_name, category):
    _value, mapped = _forage_value(source_name)
    assert mapped == category


def test_every_search_filter_is_a_real_landscape_category():
    assert "Meadows" in FORAGE_CATEGORIES
    assert "Pastures" in FORAGE_CATEGORIES
    assert "Low-forage arable crops" in FORAGE_CATEGORIES


def test_lv95_map_points_convert_back_near_st_gallen():
    lat, lon = _lv95_to_wgs84(2_746_301, 1_255_286)
    assert abs(lat - 47.4321) < 0.001
    assert abs(lon - 9.3780) < 0.001
