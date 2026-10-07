"""AI-assisted test generation and revision: OpenAI Codex (OpenAI, n.d.-b).

See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from datetime import date, timedelta

import pytest

from ml.flowering_model import (
    BEE_RELEVANT_PARAMETERS,
    FORAGE_PHENOLOGY_PARAMETERS,
    FloweringModel,
)


def test_persisted_model_predicts_a_bounded_signal():
    model = FloweringModel.load("model/flowering_model.joblib")
    assert model is not None
    dates = [
        (date(2027, 4, 15) + timedelta(days=index)).isoformat() for index in range(7)
    ]
    result = model.predict_signal(47.4245, 9.3767, 675, dates)
    assert result["available"]
    assert 0 <= result["score"] <= 100
    assert result["model_mae_days"] < result["baseline_mae_days"]
    assert result["predictions"]


@pytest.mark.parametrize("height, expected", [(None, 600.0), (0.0, 0.0)])
def test_height_imputation_only_replaces_missing_values(monkeypatch, height, expected):
    model = FloweringModel.load("model/flowering_model.joblib")
    original_predict = model.pipeline.predict
    captured = []

    def capture(frame):
        captured.extend(frame["height_m"])
        return original_predict(frame)

    monkeypatch.setattr(model.pipeline, "predict", capture)
    model.predict_signal(47.4245, 9.3767, height, ["2027-04-15"])
    assert captured and all(value == expected for value in captured)


def test_orchard_filter_uses_matching_observed_species():
    model = FloweringModel.load("model/flowering_model.joblib")
    dates = [
        (date(2027, 4, 15) + timedelta(days=index)).isoformat() for index in range(30)
    ]

    result = model.predict_signal(
        47.4245,
        9.3767,
        675,
        dates,
        "Orchards and high-stem fruit trees",
    )

    assert result["category_focus_applied"]
    assert {item["species"] for item in result["predictions"]} <= {
        "Apple tree - flowering (50%)",
        "Cherry tree - flowering (50%)",
        "Pear tree - flowering (50%)",
    }


def test_signal_can_cross_a_calendar_year():
    model = FloweringModel.load("model/flowering_model.joblib")
    dates = [
        (date(2026, 12, 20) + timedelta(days=index)).isoformat() for index in range(30)
    ]

    result = model.predict_signal(47.4245, 9.3767, 675, dates)

    assert len(result["daily"]) == 30
    assert result["daily"][0]["date"] == "2026-12-20"
    assert result["daily"][-1]["date"] == "2027-01-18"


def test_regional_and_grassland_signals_exclude_wind_pollinated_grasses_and_birch():
    assert "mbetp65d" not in BEE_RELEVANT_PARAMETERS
    assert "mdacg65d" not in BEE_RELEVANT_PARAMETERS
    assert "mdacg65d" not in FORAGE_PHENOLOGY_PARAMETERS["Meadows"]
