from uuid import uuid4

from app.api.agents import KnowledgeConfig, VersionCreate
from app.api.chat import build_knowledge_context


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
