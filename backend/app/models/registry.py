"""统一 SQLAlchemy ORM 模型注册表。

职责：确保所有数据库会话进程在首次 ORM flush/query 前加载完整的声明式模型元数据。
边界：只负责模型模块注册，不创建数据库连接、不执行 migration。

原因：部分模型通过字符串 ForeignKey 引用跨模块表（例如 `model_profiles`）。
如果业务进程只导入了其中一个模型模块，SQLAlchemy 在 mapper configure 时会因为
目标表尚未注册到 Base.metadata 而抛出 NoReferencedTableError。数据库 migration
本身已经存在这些表，因此这里解决的是运行时 ORM metadata 注册完整性问题。
"""

# Keep imports explicit and side-effect-only: importing a model module registers its
# Table/Mapper with the shared Base.metadata. noqa is intentional for registry imports.
from app.models.agent_delegation import AgentDelegation  # noqa: F401
from app.models.execution import Execution, ExecutionEvent  # noqa: F401
from app.models.integration_event import IntegrationEventRecord  # noqa: F401
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentVersion  # noqa: F401
from app.models.model_provider import ModelProfile, ModelProvider  # noqa: F401
from app.models.organization import Organization, OrganizationMembership  # noqa: F401
from app.models.usage import ModelUsageRecord  # noqa: F401
from app.models.webhook_delivery import WebhookDelivery  # noqa: F401
from app.models.webhook_integration import WebhookDestination, WebhookSubscription  # noqa: F401
from app.models.workflow import Workflow, WorkflowVersion  # noqa: F401
from app.models.workflow_circuit import WorkflowCircuitState  # noqa: F401
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution  # noqa: F401
from app.models.workflow_trace import WorkflowTraceEvent  # noqa: F401
from app.models.workflow_trigger import WorkflowTrigger  # noqa: F401
