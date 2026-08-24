"""Runtime 与 Knowledge 集成契约测试。

模块职责：验证 Agent API 的知识配置契约与 Chat 知识上下文拼装行为。
边界：只验证已迁移的 API v1 Agent 入口，不保留旧 API 模块兼容导入。
关键依赖：Agent v1 API schema、Chat API 的知识上下文构建函数。
"""

from uuid import uuid4

from app.api.v1.agents.chat import build_knowledge_context
from app.api.v1.agents.router import KnowledgeConfig, VersionCreate


def test_knowledge_config_contract_defaults_are_safe():
    config = KnowledgeConfig()
    assert config.knowledge_base_ids == []
    assert config.top_k == 5


def test_version_create_exposes_knowledge_config_contract():
    knowledge_base_id = uuid4()
    payload = VersionCreate(
        system_prompt="回答企业问题",
        model_id="mock-model",
        knowledge_config={"knowledge_base_ids": [knowledge_base_id], "top_k": 3},
    )
    assert payload.knowledge_config.top_k == 3
    assert payload.knowledge_config.knowledge_base_ids == [knowledge_base_id]


def test_knowledge_context_preserves_citations_before_model_context():
    context = build_knowledge_context(
        [
            {"citation": "员工手册#0", "content": "请假需要提前申请。"},
            {"citation": "制度文档#2", "content": "审批由直属主管完成。"},
        ]
    )
    assert "员工手册#0" in context
    assert "制度文档#2" in context
    assert "请假需要提前申请。" in context
    assert "审批由直属主管完成。" in context
