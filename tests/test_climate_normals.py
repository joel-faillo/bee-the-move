from datetime import date

import numpy as np

from services.climate_normals import ClimateNormalsService, _month_spans


def test_month_spans_count_an_inclusive_cross_month_period():
    assert _month_spans(date(2026, 4, 20), date(2026, 5, 9)) == [
        (date(2026, 4, 1), 11),
        (date(2026, 5, 1), 9),
    ]


def test_summary_weights_monthly_normals_to_the_planned_stay():
    service = ClimateNormalsService("unused-in-unit-test.npz")
    eastings = np.array([2_600_000.0])
    northings = np.array([1_200_000.0])
    temperature = np.zeros((12, 1, 1))
    precipitation = np.zeros((12, 1, 1))
    sunshine = np.zeros((12, 1, 1))
    temperature[3, 0, 0], temperature[4, 0, 0] = 10, 20
    precipitation[3, 0, 0], precipitation[4, 0, 0] = 60, 93
    sunshine[3, 0, 0], sunshine[4, 0, 0] = 40, 60
    service._grids = {
        "temperature_c": (temperature, eastings, northings),
        "precipitation_mm": (precipitation, eastings, northings),
        "relative_sunshine_percent": (sunshine, eastings, northings),
    }

    result = service.summary(
        2_600_000,
        1_200_000,
        "2026-04-20",
        "2026-05-09",
    )

    assert result["available"]
    assert result["period_days"] == 20
    assert result["temperature_c"] == 14.5
    assert result["precipitation_mm"] == 49.0
    assert result["relative_sunshine_percent"] == 49.0


def test_bundled_official_snapshot_covers_a_swiss_grid_point():
    result = ClimateNormalsService(
        "data/climate_normals_1991_2020.npz"
    ).summary(2_746_000, 1_255_000, "2027-04-15", "2027-05-12")

    assert result["normal_period"] == "1991-2020"
    assert result["source_snapshot"] == "30/09/2026"
    assert 0 < result["temperature_c"] < 25
    assert result["precipitation_mm"] > 0
    assert 0 < result["relative_sunshine_percent"] <= 100
