from datetime import date, timedelta

from ml.flowering_model import FloweringModel


def test_persisted_model_predicts_a_bounded_signal():
    model = FloweringModel.load("model/flowering_model.joblib")
    assert model is not None
    dates = [(date(2027, 4, 15) + timedelta(days=index)).isoformat() for index in range(7)]
    result = model.predict_signal(47.4245, 9.3767, 675, dates)
    assert result["available"]
    assert 0 <= result["score"] <= 100
    assert result["model_mae_days"] < result["baseline_mae_days"]
    assert result["predictions"]
