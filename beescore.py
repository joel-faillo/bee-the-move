"""Pure, bounded and deliberately small regional-screening formula.

The index answers one narrow question: which candidate region has the strongest
*modelled* combination of flowering, mapped agricultural forage and continuity
during the planned stay? It does not approve a parcel or predict honey yield.

Travel practicality and short-term flight weather stay visible, but neither can
make the same landscape look biologically better or worse. Pollen, elevation,
climate normals and map-only habitat context also remain outside the score
because the available sources do not justify converting them into extra points.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

from statistics import mean, pstdev

WEIGHTS = {
    # These are transparent project choices, not official MeteoSwiss or
    # apicultural thresholds. Resource availability receives most weight;
    # continuity prevents a brief flowering peak from dominating the ranking.
    "forage": 75.0,
    "continuity": 25.0,
}


def weather_score(days: list[dict]) -> float:
    """Summarise up to seven forecast days as operational flight context.

    This is deliberately excluded from the regional index: forecasts change
    every day and cannot describe the longer-term quality of a landscape.
    """
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
    """Combine seasonal timing (65%) with mapped agricultural forage (35%).

    The larger flowering share rewards resources expected to be in bloom during
    the stay instead of counting mapped crops as if they flowered all year. The
    65/35 split is an explainable prototype assumption, not an official rule.
    """
    return round(0.65 * flowering + 0.35 * landscape, 1)


def continuity_score(flowering_days: list[dict], diversity: float) -> float:
    """Reward stable flowering (70%) and mapped category diversity (30%).

    Subtracting 1.5 standard deviations penalises short isolated peaks. Category
    diversity is only a proxy: it does not prove simultaneous flowering or field
    accessibility, so this component remains a prototype heuristic.
    """
    values = [
        float(day["score"])
        for day in flowering_days
        if day.get("score") is not None
    ]
    if not values:
        return round(0.35 * diversity, 1)
    stable = max(0.0, mean(values) - 1.5 * pstdev(values))
    return round(0.7 * stable + 0.3 * diversity, 1)


def distance_score(distance_km: float) -> float:
    """Return visible logistics context: 100 at the origin, zero from 50 km.

    The search radius deliberately does not enter this calculation. Changing a
    filter must not change an otherwise identical destination. This value is
    never included in the biological regional index.
    """
    return round(max(0, 100 - 2 * max(0, distance_km)), 1)


def calculate(
    forage: float,
    flight_weather: float | None,
    continuity: float,
    logistics: float,
) -> dict:
    """Return a biological regional index plus separate decision context.

    ``logistics`` remains visible to the beekeeper but is not a score input: a
    shorter drive does not improve forage for the colony.
    """
    ranking_components = {
        "forage": forage,
        "continuity": continuity,
    }
    available = {name: _bounded(value) for name, value in ranking_components.items()}
    total = sum(available[name] * WEIGHTS[name] for name in WEIGHTS) / 100
    return {
        "score": int(total + 0.5),
        "components": {
            "forage": round(available["forage"], 1),
            "flight_weather": (
                round(_bounded(flight_weather), 1)
                if flight_weather is not None
                else None
            ),
            "continuity": round(available["continuity"], 1),
            "logistics": round(_bounded(logistics), 1),
        },
        "applied_weights": WEIGHTS.copy(),
        "forecast_confirmed": flight_weather is not None,
    }


def best_period(weather_days: list[dict], flowering_days: list[dict]) -> dict | None:
    """Find the best three-day operational window inside the live forecast.

    The window uses 55% bee-flight weather and 45% modelled flowering. It helps
    time a move within the short forecast horizon; it is not evidence that the
    destination is suitable for the colony's complete stay.
    """
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
    return {
        "from": daily[start][0],
        "to": daily[end][0],
        "days": end - start + 1,
    }


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
