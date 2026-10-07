"""Environment-only runtime settings; scientific assumptions live in code.

AI-assisted code generation and revision: OpenAI Codex (OpenAI, n.d.-b).
See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load optional local settings before class attributes read the environment.
# Existing environment variables (including Streamlit secrets) keep priority.
load_dotenv(Path(__file__).with_name(".env"))


class Config:
    HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "8"))
    OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY", "").strip()
    FLOWERING_MODEL_PATH = os.getenv(
        "FLOWERING_MODEL_PATH", "model/flowering_model.joblib"
    )
    CLIMATE_NORMALS_PATH = os.getenv(
        "CLIMATE_NORMALS_PATH", "data/climate_normals_1991_2020.npz"
    )
