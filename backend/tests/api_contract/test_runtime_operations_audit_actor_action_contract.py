"""II-07 Runtime 运维审计动作与结果组合过滤 Contract 测试。

职责：验证动作 + 结果组合过滤的公开查询契约与数据库索引声明。
边界：只检查应用元数据，不启动服务，不访问真实数据库。
"""

from app.main import app
from app.models.runtime_operations import RuntimeOperationAudit


def test_runtime_audit_query_exposes_action_and_outcome_filters():
    """验证既有 GET 审计查询同时暴露 action 与 outcome 可选过滤。"""
    parameters = app.openapi()["paths"]["/api/v1/runtime/operations/audit/query"]["get"]["parameters"]
    names = {parameter["name"] for parameter in parameters}
    assert "action" in names
    assert "outcome" in names


def test_runtime_audit_model_declares_action_outcome_composite_index():
    """验证模型声明与迁移一致的 tenant + action + outcome + created_at 索引。"""
    index_names = {index.name for index in RuntimeOperationAudit.__table__.indexes}
    assert "ix_runtime_operation_audit_tenant_action_outcome" in index_names
