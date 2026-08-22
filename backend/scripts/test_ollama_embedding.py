from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow `uv run python scripts/test_ollama_embedding.py` from backend root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.ollama_embedding_provider import OllamaEmbeddingProvider


async def main() -> None:
    if settings.embedding_provider != "ollama":
        raise SystemExit(
            f"Expected EMBEDDING_PROVIDER=ollama, got {settings.embedding_provider!r}"
        )
    if not settings.embedding_base_url or not settings.embedding_model:
        raise SystemExit("Embedding base URL and model must be configured")

    print("provider =", settings.embedding_provider)
    print("base_url =", settings.embedding_base_url)
    print("model =", settings.embedding_model)
    print("expected_dimension =", settings.embedding_dimension)

    provider = OllamaEmbeddingProvider(
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
        timeout_seconds=settings.embedding_timeout_seconds,
        expected_dimension=settings.embedding_dimension,
    )
    vectors = await provider.embed(["维度测试"])

    actual_dimension = len(vectors[0])
    print("vector_count =", len(vectors))
    print("actual_dimension =", actual_dimension)
    print("provider_dimension =", provider.dimension)
    print("status = PASS")


if __name__ == "__main__":
    asyncio.run(main())
