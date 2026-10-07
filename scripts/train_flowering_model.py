"""Refresh the flowering model from the current MeteoSwiss open data.

AI-assisted code generation and revision: OpenAI Codex (OpenAI, n.d.-b).
See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from ml.flowering_model import train_and_save
from services.http import HttpClient


if __name__ == "__main__":
    result = train_and_save(
        HttpClient(timeout=30, cache_ttl=0), "model/flowering_model.joblib"
    )
    print(result)
