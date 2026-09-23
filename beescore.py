"""Pure, bounded and deliberately small BeeScore formula.

Only four explainable components receive weight. Pollen and elevation remain
visible context but never enter this calculation.
"""

from __future__ import annotations

from statistics import mean, pstdev

WEIGHTS = {
    "forage": 45.0,
    "flight_weather": 30.0,
    "continuity": 15.0,
    "logistics": 10.0,
}


def weather_score(days: list[dict]) -> float:
    """Average forecast flight suitability, not the entire calendar day."""
    scores = [
        day["flight_score"] for day in days[:7] if day.get("flight_score") is not None
    ]
    if scores:
        return round(mean(scores), 1)
    fallback = []
    for day in days[:7]:
        temperature, rain = day.get("temperature"), day.get("rain_mm")
        if temperature is None and rain is None:
            continue
        temperature_part = (
            _band_score(temperature, 7, 14, 30, 36) if temperature is not None else 50
        )
        fallback.append(
            0.6 * temperature_part + 0.4 * max(0, 100 - 35 * max(0, rain or 0))
        )
    return round(mean(fallback), 1) if fallback else 0


def forage_score(flowering: float, landscape: float) -> float:
    """Combine time-sensitive bloom evidence with mapped forage abundance."""
    return round(0.65 * flowering + 0.35 * landscape, 1)


def continuity_score(flowering_days: list[dict], diversity: float) -> float:
    """Reward a stable seven-day signal and multiple forage categories."""
    values = [
        float(day["score"])
        for day in flowering_days[:7]
        if day.get("score") is not None
    ]
    if not values:
        return round(0.35 * diversity, 1)
    stable = max(0.0, mean(values) - 1.5 * pstdev(values))
    return round(0.7 * stable + 0.3 * diversity, 1)


def distance_score(distance_km: float, radius_km: float) -> float:
    """Logistics only: this does not describe biological site quality."""
    return round(max(0, 100 * (1 - distance_km / max(radius_km, 1))), 1)


def calculate(
    forage: float, flight_weather: float, continuity: float, logistics: float
) -> dict:
    components = {
        "forage": _bounded(forage),
        "flight_weather": _bounded(flight_weather),
        "continuity": _bounded(continuity),
        "logistics": _bounded(logistics),
    }
    total = sum(components[name] * weight for name, weight in WEIGHTS.items()) / sum(
        WEIGHTS.values()
    )
    return {
        "score": int(total + 0.5),
        "components": {name: round(value, 1) for name, value in components.items()},
    }


def best_period(weather_days: list[dict], flowering_days: list[dict]) -> dict | None:
    flower_by_date = {item["date"]: item["score"] for item in flowering_days}
    daily = []
    for day in weather_days[:7]:
        weather = day.get("flight_score")
        if weather is None:
            weather = weather_score([day])
        daily.append(
            (day["date"], 0.55 * weather + 0.45 * flower_by_date.get(day["date"], 0))
        )
    if not daily:
        return None
    windows = [
        (index, sum(score for _, score in daily[index : index + 3]))
        for index in range(max(1, len(daily) - 2))
    ]
    start = max(windows, key=lambda item: item[1])[0]
    end = min(start + 2, len(daily) - 1)
    return {"from": daily[start][0], "to": daily[end][0]}


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _band_score(
    value: float,
    outer_low: float,
    ideal_low: float,
    ideal_high: float,
    outer_high: float,
) -> float:
    if ideal_low <= value <= ideal_high:
        return 100
    if value <= outer_low or value >= outer_high:
        return 0
    if value < ideal_low:
        return 100 * (value - outer_low) / (ideal_low - outer_low)
    return 100 * (outer_high - value) / (outer_high - ideal_high)
