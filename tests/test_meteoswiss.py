from services.meteoswiss import MeteoSwissForecastService, _flight_hour_score


def test_all_declared_weather_inputs_contribute_to_flight_suitability():
    assert MeteoSwissForecastService.PARAMETERS == (
        "tre200h0",
        "rre150h0",
        "fu3010h0",
        "fu3010h1",
        "gre000h0",
    )
    favourable = {
        "temperature": 22,
        "rain_mm": 0,
        "wind_kmh": 8,
        "gust_kmh": 12,
        "radiation_wm2": 300,
    }
    poor = {
        "temperature": 5,
        "rain_mm": 4,
        "wind_kmh": 40,
        "gust_kmh": 60,
        "radiation_wm2": 25,
    }
    assert _flight_hour_score(favourable) > _flight_hour_score(poor)


def test_daily_summary_uses_daylight_hours_and_all_weather_outputs():
    hours = [
        {
            "temperature": 10,
            "rain_mm": 1,
            "wind_kmh": 4,
            "gust_kmh": 7,
            "radiation_wm2": 0,
        },
        {
            "temperature": 20,
            "rain_mm": 0.2,
            "wind_kmh": 10,
            "gust_kmh": 15,
            "radiation_wm2": 250,
        },
    ]

    result = MeteoSwissForecastService._summarise_day("2026-09-29", hours)

    assert result["flight_hours"] == 1
    assert result["temperature"] == 20
    assert result["rain_mm"] == 0.2
    assert result["wind_kmh"] == 10
    assert result["gust_kmh"] == 15
    assert result["radiation_wm2"] == 250
