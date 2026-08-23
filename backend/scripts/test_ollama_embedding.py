from __future__ import annotations

"""Ollama Embedding 本地验证脚本。

职责：验证本地 Ollama Embedding Provider 的配置、请求和向量维度。
边界：只负责场景验证与结果输出，不实现 Provider；正式 Provider 统一由
``app.infrastructure.providers.ollama_embedding`` 提供。
依赖：项目配置、Infrastructure Provider，以及可访问的 Ollama 服务。
"""

import asyncio
import sys
from pathlib import Path

# 允许从 backend 根目录执行 `uv run python scripts/test_ollama_embedding.py`。
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.infrastructure.providers.ollama_embedding import OllamaEmbeddingProvider


async def main() -> None:
    """验证 Ollama Provider 的实际向量生成和维度契约。"""
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
