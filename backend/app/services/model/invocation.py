"""Model Provider Runtime invocation boundary.

Keeps external model invocation outside the domain provider CRUD service while
making the invocation lifecycle observable through the durable Integration Event
contract. The caller owns the surrounding business transaction; this service
never commits it.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from app.infrastructure.providers.model import ModelProvider, ModelResult
from app.services.integration.publisher import RuntimeIntegrationEventPublisher


class ModelProviderInvocationService:
    """Execute a provider call and persist only its durable runtime fact."""

    def __init__(self, publisher: RuntimeIntegrationEventPublisher):
        self.publisher = publisher

    async def complete(
        self,
        *,
        provider: ModelProvider,
        model: str,
        messages: list[dict],
        parameters: dict | None,
        tenant_id: Any,
        execution_id: Any,
        agent_id: Any,
        provider_id: Any,
        profile_id: Any | None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ModelResult:
        """Invoke ``complete`` and emit succeeded/failed in the same DB transaction.

        Prompt/messages and completion content never enter the Integration Event.
        """
        try:
            result = await provider.complete(model, messages, parameters)
        except Exception as exc:
            await self.publisher.publish_agent_model(
                tenant_id=tenant_id,
                execution_id=execution_id,
                agent_id=agent_id,
                provider_id=provider_id,
                profile_id=profile_id,
                status="failed",
                model_name=model,
                request_id=request_id,
                trace_id=trace_id,
                error_code=type(exc).__name__,
            )
            raise

        metadata = None
        if result.usage is not None:
            metadata = {
                "usage": {
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                    "total_tokens": result.usage.total_tokens,
                }
            }
        await self.publisher.publish_agent_model(
            tenant_id=tenant_id,
            execution_id=execution_id,
            agent_id=agent_id,
            provider_id=provider_id,
            profile_id=profile_id,
            status="succeeded",
            model_name=result.model or model,
            request_id=request_id,
            trace_id=trace_id,
            metadata=metadata,
        )
        return result


__all__ = ["ModelProviderInvocationService"]
