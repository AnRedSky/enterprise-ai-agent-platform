from app.runtime.memory_context import build_memory_context


class Record:
    def __init__(self, memory_type: str, memory_key: str, content: str):
        self.memory_type = memory_type
        self.memory_key = memory_key
        self.content = content


def test_memory_context_is_bounded():
    records = [Record("fact", "name", "Alice"), Record("preference", "language", "中文")]
    context = build_memory_context(records, max_chars=200)
    assert context is not None
    assert "Alice" in context
    assert "中文" in context


def test_empty_memory_returns_none():
    assert build_memory_context([]) is None
