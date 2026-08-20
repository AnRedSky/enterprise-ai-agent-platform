from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# When a script is executed by file path, Python puts ``backend/scripts`` on
# sys.path instead of the backend project root. Add the project root explicitly
# so the probe always imports the same application package used by ``uv run``.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.embedding_provider import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider


async def validate() -> int:
    if settings.embedding_provider != "openai-compatible":
        print(
            "Embedding provider probe skipped: set EMBEDDING_PROVIDER=openai-compatible "
            "to validate a real provider."
        )
        return 0

    missing = [
        name
        for name, value in {
            "EMBEDDING_BASE_URL": settings.embedding_base_url,
            "EMBEDDING_API_KEY": settings.embedding_api_key,
            "EMBEDDING_MODEL": settings.embedding_model,
        }.items()
        if not value
    ]
    if missing:
        print(f"Missing embedding provider settings: {', '.join(missing)}")
        return 2

    provider = OpenAICompatibleEmbeddingProvider(
        base_url=settings.embedding_base_url or "",
        api_key=settings.embedding_api_key or "",
        model=settings.embedding_model or "",
        timeout_seconds=settings.embedding_timeout_seconds,
    )
    try:
        vectors = await provider.embed(["Enterprise AI Agent Platform retrieval validation"])
    except EmbeddingProviderError as exc:
        print(f"Embedding provider validation failed: {exc}")
        return 1

    if not vectors or not vectors[0]:
        print("Embedding provider validation failed: empty vector")
        return 1

    print(
        "Embedding provider validation passed: "
        f"provider={settings.embedding_provider}, model={settings.embedding_model}, "
        f"dimensions={len(vectors[0])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(validate()))
