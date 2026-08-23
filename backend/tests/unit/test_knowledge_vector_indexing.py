from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.knowledge import KnowledgeVectorIndexingService
from app.services.vector_retrieval_provider import VectorRetrievalProviderError


def _chunk(index: int):
    return SimpleNamespace(id=uuid4(), chunk_index=index, content_hash=f"hash-{index}", content=f"chunk {index}")


def test_build_records_preserves_chunk_order_and_scope_metadata():
    kb_id = uuid4()
    version_id = uuid4()
    chunks = [_chunk(0), _chunk(1)]
    records = KnowledgeVectorIndexingService.build_records(chunks, [[1.0, 0.0], [0.0, 1.0]], kb_id, version_id)
    assert [record.chunk_id for record in records] == [str(chunk.id) for chunk in chunks]
    assert records[0].embedding == (1.0, 0.0)
    assert records[1].metadata["knowledge_base_id"] == str(kb_id)
    assert records[1].metadata["document_version_id"] == str(version_id)
    assert records[1].metadata["chunk_index"] == "1"


def test_build_records_rejects_embedding_count_mismatch():
    with pytest.raises(VectorRetrievalProviderError, match="embedding count"):
        KnowledgeVectorIndexingService.build_records([_chunk(0), _chunk(1)], [[1.0, 0.0]], uuid4(), uuid4())
