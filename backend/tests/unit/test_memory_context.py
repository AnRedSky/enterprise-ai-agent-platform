"""Memory Runtime 上下文单元测试。

模块职责：验证 Memory 记录向模型参考上下文的有界渲染行为。
边界：不访问数据库、不验证 Memory Service；只覆盖纯函数格式化逻辑。
关键外部依赖：app.runtime.memory.context。
"""

from app.runtime.memory import build_memory_context


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
