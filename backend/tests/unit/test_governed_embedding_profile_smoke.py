from __future__ import annotations

import pytest

from scripts.evaluation.knowledge import run_governed_embedding_profile_smoke as smoke


@pytest.mark.asyncio
async def test_governed_smoke_model_dimension_uses_production_ollama_adapter(monkeypatch):
    calls: list[tuple[str, str]] = []

    class FakeProvider:
        def __init__(self, *, base_url: str, model: str, timeout_seconds: float):
            calls.append((base_url, model))

        async def embed(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["governed evaluation smoke test"]
            return [[0.1, 0.2, 0.3, 0.4]]

    monkeypatch.setattr(smoke, "OllamaEmbeddingProvider", FakeProvider)

    dimension = await smoke._model_dimension("http://localhost:11434", "nomic-embed-text:latest")

    assert dimension == 4
    assert calls == [("http://localhost:11434", "nomic-embed-text:latest")]


def test_governed_smoke_rejects_profile_dimension_mismatch_before_fixture_creation(monkeypatch):
    monkeypatch.setattr(smoke.settings, "embedding_dimension", 768)

    with pytest.raises(SystemExit, match="pgvector storage contract requires dimension=768"):
        smoke._assert_storage_dimension((768, 1024))
