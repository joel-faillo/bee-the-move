"""Refresh the flowering model from the current MeteoSwiss open data.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from ml.flowering_model import train_and_save
from services.http import HttpClient


if __name__ == "__main__":
    result = train_and_save(HttpClient(timeout=30, cache_ttl=0), "model/flowering_model.joblib")
    print(result)
