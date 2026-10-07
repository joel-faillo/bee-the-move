"""Pure, bounded and deliberately small regional-screening formula.

The index answers one narrow question: which candidate region has the strongest
*modelled* combination of flowering, mapped agricultural forage and continuity
during the planned stay? It does not approve a parcel or predict honey yield.

Travel practicality and short-term flight weather stay visible, but neither can
make the same landscape look biologically better or worse. Pollen, elevation,
climate normals and map-only habitat context also remain outside the score
because the available sources do not justify converting them into extra points.

AI-assisted code generation and revision: OpenAI Codex (OpenAI, n.d.-b).
See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from __future__ import annotations

from datetime import date
from statistics import mean, pstdev

WEIGHTS = {
    # These are transparent project choices, not official MeteoSwiss or
    # apicultural thresholds. Resource availability receives most weight;
    # continuity prevents a brief flowering peak from dominating the ranking.
    "forage": 75.0,
    "continuity": 25.0,
}


def weather_score(days: list[dict]) -> float | None:
    """Summarise up to seven forecast days as operational flight context.

    This is deliberately excluded from the regional index: forecasts change
    every day and cannot describe the longer-term quality of a landscape.
    """
    scores = [
        day["flight_score"] for day in days[:7] if day.get("flight_score") is not None
    ]
    # No temperature/rain-only fallback: missing wind or daylight information
    # must remain unavailable rather than become an invented flight estimate.
    return round(mean(scores), 1) if scores else None


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
        float(day["score"]) for day in flowering_days if day.get("score") is not None
    ]
    stable = max(0.0, mean(values) - 1.5 * pstdev(values)) if values else 0.0
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
            continue
        daily.append(
            (day["date"], 0.55 * weather + 0.45 * flower_by_date.get(day["date"], 0))
        )
    if not daily:
        return None
    daily.sort()
    # A missing forecast date must not create an apparently continuous window.
    # Prefer three real consecutive days; shorter horizons remain explicit.
    for length in range(min(3, len(daily)), 0, -1):
        windows = [
            daily[index : index + length] for index in range(len(daily) - length + 1)
        ]
        consecutive = [
            window
            for window in windows
            if (
                date.fromisoformat(window[-1][0]) - date.fromisoformat(window[0][0])
            ).days
            == length - 1
        ]
        if consecutive:
            best = max(
                consecutive, key=lambda window: mean(score for _, score in window)
            )
            return {"from": best[0][0], "to": best[-1][0], "days": length}


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))
