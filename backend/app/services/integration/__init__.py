"""Enterprise Integration 领域入口。"""

from app.services.integration.contract import IntegrationEvent
from app.services.integration.repository import IntegrationEventRepository

__all__ = ["IntegrationEvent", "IntegrationEventRepository"]
