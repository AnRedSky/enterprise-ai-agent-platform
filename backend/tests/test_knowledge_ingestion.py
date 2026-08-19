from app.services.knowledge_ingestion import KnowledgeIngestionService


def test_normalize_text_collapses_whitespace_and_blank_lines():
    text = "  hello\r\n\r\n\r\nworld  "
    assert KnowledgeIngestionService.normalize_text(text) == "hello\n\nworld"


def test_chunk_text_is_deterministic_and_tracks_offsets():
    text = "第一段\n第二段\n第三段\n第四段"
    chunks = KnowledgeIngestionService.chunk_text(text, max_chars=10, overlap_chars=2)
    assert len(chunks) >= 2
    assert [item["chunk_index"] for item in chunks] == list(range(len(chunks)))
    assert all(item["char_start"] < item["char_end"] for item in chunks)
    assert all(item["content_hash"] for item in chunks)
    assert chunks == KnowledgeIngestionService.chunk_text(text, max_chars=10, overlap_chars=2)


def test_chunk_text_rejects_invalid_overlap():
    try:
        KnowledgeIngestionService.chunk_text("hello", max_chars=100, overlap_chars=100)
    except ValueError as exc:
        assert "smaller than max_chars" in str(exc)
    else:
        raise AssertionError("invalid overlap should raise ValueError")


def test_empty_content_returns_no_chunks():
    assert KnowledgeIngestionService.chunk_text("   \n\n ") == []
