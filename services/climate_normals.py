"""Long-term climate context from MeteoSwiss spatial climate normals.

The official 1991-2020 monthly grids describe typical temperature,
precipitation and relative sunshine across Switzerland. They are historical
reference values, never a forecast for the user's planned dates.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

import calendar
import threading
from datetime import date, timedelta
from pathlib import Path

import numpy as np

GRID_NAMES = (
    "temperature_c",
    "precipitation_mm",
    "relative_sunshine_percent",
)


class ClimateNormalsService:
    """Read the nearest 1 km grid cell for a planned period."""

    def __init__(self, data_path: str | Path) -> None:
        self.data_path = Path(data_path)
        self._grids: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None
        self._source_snapshot: str | None = None
        self._source_item_updated: str | None = None
        self._lock = threading.Lock()

    def summary(
        self,
        easting: float,
        northing: float,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Return day-weighted monthly normals for the requested stay."""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("The planned end date must not precede the arrival date")
        self._ensure_loaded()
        assert self._grids is not None

        month_spans = _month_spans(start, end)
        monthly = []
        totals = {
            "temperature_c": 0.0,
            "relative_sunshine_percent": 0.0,
            "precipitation_mm": 0.0,
        }
        total_days = (end - start).days + 1
        for month_start, days in month_spans:
            month_index = month_start.month - 1
            values = {
                name: _nearest_value(grid, eastings, northings, month_index, easting, northing)
                for name, (grid, eastings, northings) in self._grids.items()
            }
            days_in_month = calendar.monthrange(month_start.year, month_start.month)[1]
            precipitation = values["precipitation_mm"] * days / days_in_month
            totals["temperature_c"] += values["temperature_c"] * days
            totals["relative_sunshine_percent"] += (
                values["relative_sunshine_percent"] * days
            )
            totals["precipitation_mm"] += precipitation
            monthly.append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "days_in_period": days,
                    "temperature_c": round(values["temperature_c"], 1),
                    "precipitation_mm": round(precipitation, 1),
                    "relative_sunshine_percent": round(
                        values["relative_sunshine_percent"], 1
                    ),
                }
            )
        return {
            "available": True,
            "normal_period": "1991-2020",
            "period_days": total_days,
            "temperature_c": round(totals["temperature_c"] / total_days, 1),
            "precipitation_mm": round(totals["precipitation_mm"], 1),
            "relative_sunshine_percent": round(
                totals["relative_sunshine_percent"] / total_days, 1
            ),
            "monthly": monthly,
            "source_snapshot": self._source_snapshot,
            "source_item_updated": self._source_item_updated,
            "method": (
                "Nearest MeteoSwiss 1 km grid cell; monthly 1991-2020 normals "
                "weighted by the days included in the planned period"
            ),
        }

    def _ensure_loaded(self) -> None:
        if self._grids is not None:
            return
        with self._lock:
            if self._grids is not None:
                return
            if not self.data_path.exists():
                raise RuntimeError("The bundled MeteoSwiss climate-normal snapshot is missing")
            with np.load(self.data_path) as source:
                scale = float(source["scale"])
                eastings = source["eastings"].astype(float)
                northings = source["northings"].astype(float)
                grids = {}
                for name in GRID_NAMES:
                    encoded = source[name]
                    values = encoded.astype(float) / scale
                    values[encoded == -32768] = np.nan
                    grids[name] = values, eastings, northings
                self._source_snapshot = str(source["source_snapshot"])
                self._source_item_updated = str(source["source_item_updated"])
            self._grids = grids


def _nearest_value(
    grid: np.ndarray,
    eastings: np.ndarray,
    northings: np.ndarray,
    month_index: int,
    easting: float,
    northing: float,
) -> float:
    x = int(np.abs(eastings - easting).argmin())
    y = int(np.abs(northings - northing).argmin())
    value = float(grid[month_index, y, x])
    if np.isnan(value):
        raise ValueError("No climate-normal value is available for this grid cell")
    return value


def _month_spans(start: date, end: date) -> list[tuple[date, int]]:
    """Count included days for every calendar month in an inclusive period."""
    spans = []
    cursor = start
    while cursor <= end:
        next_month = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
        segment_end = min(end, next_month - timedelta(days=1))
        spans.append((date(cursor.year, cursor.month, 1), (segment_end - cursor).days + 1))
        cursor = segment_end + timedelta(days=1)
    return spans
