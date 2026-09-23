"""Environment-only runtime settings; scientific assumptions live in code."""

from __future__ import annotations

import os


class Config:
    HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "8"))
    OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY", "").strip()
    FLOWERING_MODEL_PATH = os.getenv(
        "FLOWERING_MODEL_PATH", "model/flowering_model.joblib"
    )
