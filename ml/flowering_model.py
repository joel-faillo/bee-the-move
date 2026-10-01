"""Train and use the project's own flowering-date regression model.

AI assistance citation: OpenAI Codex helped draft this module on 21 September
2026 from the team's Bee the Move specification. The team must review this
code and record its final use in the project video and list of aids.

The target is the observed day-of-year of MeteoSwiss's 50% flowering phase.
The model never predicts nectar yield; it estimates seasonal timing only.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from services.http import HttpClient

COLLECTION = "ch.meteoschweiz.ogd-phenology"
ITEMS_URL = f"https://data.geo.admin.ch/api/stac/v1/collections/{COLLECTION}/items"
STATIONS_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-phenology/ogd-phenology_meta_stations.csv"
PARAMETERS_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-phenology/ogd-phenology_meta_parameters.csv"
FEATURES = ["parameter", "latitude", "longitude", "height_m", "year"]
FORAGE_PHENOLOGY_PARAMETERS = {
    "Orchards and high-stem fruit trees": ("mmald65d", "mprua65d", "mpyrc65d"),
    "Meadows": ("mcarp65d", "mleuv65d", "mtaro65d"),
    "Pastures": ("mcarp65d", "mleuv65d", "mtaro65d"),
}
# MeteoSwiss observes phenological indicator plants, not nectar yield. The
# regional signal therefore excludes wind-pollinated birch and cocksfoot and
# keeps flowering species with a documented nectar or pollen role for bees.
BEE_RELEVANT_PARAMETERS = (
    "maesh65d",  # horse chestnut
    "mcarp65d",  # cuckoo flower
    "mcass65d",  # sweet chestnut
    "mcora65d",  # hazel (early pollen)
    "mepia65d",  # willow herb
    "mleuv65d",  # field daisy
    "mmald65d",  # apple
    "mprua65d",  # cherry
    "mpyrc65d",  # pear
    "mrobp65d",  # robinia
    "msora65d",  # rowan
    "mtaro65d",  # dandelion
    "mtilc65d",  # small-leaved lime
    "mtilp65d",  # large-leaved lime
    "mtusf65d",  # coltsfoot
)


@dataclass(frozen=True)
class FloweringPrediction:
    parameter: str
    species: str
    day_of_year: float
    lower_day: float
    upper_day: float


class FloweringModel:
    """Small wrapper around the persisted scikit-learn pipeline."""

    def __init__(self, artifact: dict) -> None:
        self.pipeline: Pipeline = artifact["pipeline"]
        self.parameters: dict[str, str] = artifact["parameters"]
        self.metrics: dict = artifact["metrics"]
        self.metadata: dict = artifact["metadata"]

    @classmethod
    def load(cls, path: str | Path) -> "FloweringModel | None":
        model_path = Path(path)
        return cls(joblib.load(model_path)) if model_path.exists() else None

    def predict_signal(
        self,
        lat: float,
        lon: float,
        height_m: float | None,
        dates: list[str],
        preferred_category: str | None = None,
    ) -> dict:
        """Predict flowering timing across the user's complete planning period.

        Only orchard, meadow and pasture filters have direct species matches in
        the official phenology dataset. Other agricultural filters still use
        their mapped area, while flowering remains the general regional signal.
        """
        if not dates:
            return {"available": False, "daily": [], "score": 0}
        years = sorted({date.fromisoformat(value).year for value in dates})
        selected_parameters = FORAGE_PHENOLOGY_PARAMETERS.get(preferred_category)
        candidates = selected_parameters or BEE_RELEVANT_PARAMETERS
        parameter_names = [
            parameter
            for parameter in candidates
            if parameter in self.parameters
        ]
        focus_applied = bool(selected_parameters and parameter_names)
        frame = pd.DataFrame(
            [
                {
                    "parameter": parameter,
                    "latitude": lat,
                    "longitude": lon,
                    "height_m": height_m or 600.0,
                    "year": year,
                }
                for year in years
                for parameter in parameter_names
            ]
        )
        point_predictions = self.pipeline.predict(frame[FEATURES])
        transformed = self.pipeline.named_steps["prepare"].transform(frame[FEATURES])
        forest = self.pipeline.named_steps["model"]
        tree_predictions = np.vstack(
            [tree.predict(transformed) for tree in forest.estimators_]
        )
        lower = np.quantile(tree_predictions, 0.1, axis=0)
        upper = np.quantile(tree_predictions, 0.9, axis=0)
        predictions = [
            FloweringPrediction(
                parameter=parameter,
                species=self.parameters[parameter],
                day_of_year=float(point_predictions[index]),
                lower_day=float(lower[index]),
                upper_day=float(upper[index]),
            )
            for index, parameter in enumerate(frame["parameter"])
        ]

        daily = []
        for value in dates:
            target_date = date.fromisoformat(value)
            target = target_date.timetuple().tm_yday
            signals = sorted(
                (
                    math.exp(-abs(target - item.day_of_year) / 14)
                    for item, prediction_year in zip(predictions, frame["year"])
                    if prediction_year == target_date.year
                ),
                reverse=True,
            )[:6]
            daily.append({"date": value, "score": round(100 * sum(signals) / len(signals))})

        midpoint_date = date.fromisoformat(dates[len(dates) // 2])
        midpoint = midpoint_date.timetuple().tm_yday
        midpoint_predictions = [
            item
            for item, prediction_year in zip(predictions, frame["year"])
            if prediction_year == midpoint_date.year
        ]
        closest = sorted(
            midpoint_predictions, key=lambda item: abs(item.day_of_year - midpoint)
        )[:5]
        return {
            "available": True,
            "daily": daily,
            "score": round(sum(item["score"] for item in daily) / len(daily)),
            "predictions": [
                {
                    "species": item.species,
                    "predicted_date": _date_from_day(midpoint_date.year, item.day_of_year),
                    "range_from": _date_from_day(midpoint_date.year, item.lower_day),
                    "range_to": _date_from_day(midpoint_date.year, item.upper_day),
                }
                for item in closest
            ],
            "preferred_category": preferred_category,
            "category_focus_applied": focus_applied,
            "category_focus_note": (
                "Flowering timing uses matching orchard or grassland species."
                if focus_applied
                else (
                    "This mapped forage category has no direct species match in the "
                    "MeteoSwiss phenology dataset; the regional flowering signal is used."
                    if preferred_category
                    else "General regional flowering signal."
                )
            ),
            "model": "RandomForestRegressor",
            "model_mae_days": self.metrics.get("model_mae_days"),
            "baseline_mae_days": self.metrics.get("baseline_mae_days"),
            "training_rows": self.metrics.get("training_rows"),
            "trained_at": self.metadata.get("trained_at"),
            "source_updated": self.metadata.get("source_updated"),
            "method": "Modello addestrato sulle date storiche MeteoSwiss di fioritura al 50%",
        }


def train_and_save(http: HttpClient, output_path: str | Path) -> dict:
    """Download the current official dataset, evaluate, refit and persist."""
    rows, parameters, source_updated = _download_rows(http)
    frame = pd.DataFrame(rows)
    if len(frame) < 500:
        raise RuntimeError("Insufficient phenology observations to train the model")

    latest_complete_year = date.today().year - 1
    frame = frame[frame["year"] <= latest_complete_year].copy()
    test_start = max(int(frame["year"].max()) - 4, int(frame["year"].min()) + 1)
    train = frame[frame["year"] < test_start]
    test = frame[frame["year"] >= test_start]
    if train.empty or test.empty:
        raise RuntimeError("Cannot create a chronological train/test split")

    evaluation_model = _pipeline()
    evaluation_model.fit(train[FEATURES], train["day_of_year"])
    model_predictions = evaluation_model.predict(test[FEATURES])
    medians = train.groupby("parameter")["day_of_year"].median()
    global_median = float(train["day_of_year"].median())
    baseline_predictions = test["parameter"].map(medians).fillna(global_median)

    final_model = _pipeline()
    final_model.fit(frame[FEATURES], frame["day_of_year"])
    metrics = {
        "model_mae_days": round(float(mean_absolute_error(test["day_of_year"], model_predictions)), 2),
        "baseline_mae_days": round(float(mean_absolute_error(test["day_of_year"], baseline_predictions)), 2),
        "training_rows": int(len(frame)),
        "training_years": [int(frame["year"].min()), int(frame["year"].max())],
        "test_years": [int(test["year"].min()), int(test["year"].max())],
        "test_rows": int(len(test)),
    }
    artifact = {
        "pipeline": final_model,
        "parameters": parameters,
        "metrics": metrics,
        "metadata": {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "source_updated": source_updated,
            "source": "MeteoSwiss Phenological Observations via STAC",
            "target": "day of year of 50% flowering",
        },
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Compression keeps the reproducible model small enough for the course
    # submission without changing its predictions.
    joblib.dump(artifact, output, compress=3)
    return {"metrics": metrics, "metadata": artifact["metadata"]}


def _pipeline() -> Pipeline:
    prepare = ColumnTransformer(
        [
            ("species", OneHotEncoder(handle_unknown="ignore"), ["parameter"]),
            ("numeric", StandardScaler(), ["latitude", "longitude", "height_m", "year"]),
        ]
    )
    return Pipeline(
        [
            ("prepare", prepare),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=120,
                    max_depth=18,
                    min_samples_leaf=5,
                    max_samples=0.8,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _download_rows(http: HttpClient) -> tuple[list[dict], dict[str, str], str | None]:
    station_text = http.get_text(STATIONS_URL, encoding="latin-1", cache=False)
    stations = {
        row["station_abbr"].lower(): row
        for row in csv.DictReader(io.StringIO(station_text), delimiter=";")
    }
    parameter_text = http.get_text(PARAMETERS_URL, encoding="latin-1", cache=False)
    parameters = {}
    for row in csv.DictReader(io.StringIO(parameter_text), delimiter=";"):
        description = row.get("parameter_description_en", "")
        if "flowering (50%)" in description.lower():
            parameters[row["parameter_shortname"]] = description.split(" / ")[0]

    items = http.get_json(ITEMS_URL, params={"limit": 200}, cache=False)
    source_updated = max(
        (item.get("properties", {}).get("updated", "") for item in items.get("features", [])),
        default=None,
    )
    observations = []
    for item in items.get("features", []):
        station_id = str(item.get("id", "")).lower()
        station = stations.get(station_id)
        asset = next(iter(item.get("assets", {}).values()), None)
        if not station or not asset:
            continue
        text = http.get_text(asset["href"], encoding="latin-1", cache=False)
        for row in csv.DictReader(io.StringIO(text), delimiter=";"):
            for parameter in parameters:
                raw = row.get(parameter, "")
                if not raw:
                    continue
                try:
                    observed = datetime.strptime(raw, "%Y%m%d").date()
                    height = float(station["station_height_masl"])
                    latitude = float(station["station_coordinates_wgs84_lat"])
                    longitude = float(station["station_coordinates_wgs84_lon"])
                except (ValueError, KeyError):
                    continue
                day_of_year = observed.timetuple().tm_yday
                if 20 <= day_of_year <= 330:
                    observations.append(
                        {
                            "parameter": parameter,
                            "latitude": latitude,
                            "longitude": longitude,
                            "height_m": height,
                            "year": observed.year,
                            "day_of_year": day_of_year,
                        }
                    )
    return observations, parameters, source_updated


def _date_from_day(year: int, day_value: float) -> str:
    day = max(1, min(365, int(round(day_value))))
    return datetime.strptime(f"{year}-{day:03d}", "%Y-%j").date().isoformat()
