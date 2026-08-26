"""模型 Runtime Gateway。

模块职责：为 Agent/Workflow Runtime 提供唯一模型调用入口，并选择已治理的技术 Provider。
边界：不实现领域路由或治理策略；未绑定 Model Profile 时才允许按应用配置执行本地 mock fallback。
关键外部依赖：应用 settings、infrastructure/providers 的 OpenAI-compatible 与 Mock Provider。
"""

import os
from typing import AsyncIterator
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.infrastructure.providers.mock_model import MockModelProvider
from app.infrastructure.providers.model import ModelResult
from app.infrastructure.providers.openai_model import OpenAICompatibleProvider


class ModelGateway:
    """模型统一调用入口，禁止将 Provider 技术细节泄漏到 Agent Runtime。"""

    def __init__(self, provider=None):
        self.provider = provider or (
            OpenAICompatibleProvider() if settings.model_provider == "openai-compatible" else MockModelProvider()
        )

    @staticmethod
    def _credential(provider) -> str | None:
        if provider is None or not provider.credential_ref:
            return settings.model_api_key
        return os.getenv(provider.credential_ref)

    def _provider_for_profile(self, profile=None, model_provider=None):
        if profile is None or model_provider is None:
            return self.provider
        if model_provider.provider_type in {"openai-compatible", "ollama"}:
            parameters = profile.parameters or {}
            return OpenAICompatibleProvider(
                base_url=model_provider.endpoint or settings.model_base_url,
                api_key=self._credential(model_provider),
                timeout_seconds=float(parameters.get("timeout_seconds", settings.model_timeout_seconds)),
            )
        if model_provider.provider_type == "mock":
            return MockModelProvider()
        raise HTTPException(422, f"不支持的 Model Provider 类型: {model_provider.provider_type}")

    @staticmethod
    def _request_parameters(profile) -> dict | None:
        if profile is None:
            return None
        return {key: value for key, value in (profile.parameters or {}).items() if key != "timeout_seconds"}

    @staticmethod
    def _raise_provider_http_error(exc: httpx.HTTPStatusError) -> None:
        """把已确认的 Provider HTTP 状态转换为 API 可识别的 HTTPException。

        Args:
            exc: OpenAI-compatible Provider 返回非 2xx 状态时产生的 HTTPStatusError。

        Returns:
            无；始终抛出带原始 HTTP 状态码的 HTTPException。

        Raises:
            HTTPException: Provider 已返回明确 HTTP 状态时抛出，使 Workflow Runtime 能保留真实失败码。
        """
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc

    async def generate(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
        model_profile=None,
        model_provider=None,
    ) -> ModelResult:
        provider = self._provider_for_profile(model_profile, model_provider)
        actual_model = model_profile.model_name if model_profile is not None else model
        parameters = self._request_parameters(model_profile)
        if isinstance(provider, OpenAICompatibleProvider) and actual_model.startswith("mock-"):
            provider = MockModelProvider()
        try:
            return await provider.complete(actual_model, messages, parameters)
        except httpx.HTTPStatusError as exc:
            if model_profile is not None or not settings.model_fallback_to_mock or isinstance(provider, MockModelProvider):
                self._raise_provider_http_error(exc)
            return await MockModelProvider().complete(settings.model_default_name, messages)
        except Exception:
            if model_profile is not None or not settings.model_fallback_to_mock or isinstance(provider, MockModelProvider):
                raise
            return await MockModelProvider().complete(settings.model_default_name, messages)

    async def stream(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
        model_profile=None,
        model_provider=None,
    ) -> AsyncIterator[str]:
        provider = self._provider_for_profile(model_profile, model_provider)
        actual_model = model_profile.model_name if model_profile is not None else model
        parameters = self._request_parameters(model_profile)
        if isinstance(provider, OpenAICompatibleProvider) and actual_model.startswith("mock-"):
            provider = MockModelProvider()
        try:
            async for chunk in provider.stream(actual_model, messages, parameters):
                if chunk:
                    yield chunk
        except httpx.HTTPStatusError as exc:
            if model_profile is not None or not settings.model_fallback_to_mock or isinstance(provider, MockModelProvider):
                self._raise_provider_http_error(exc)
            async for chunk in MockModelProvider().stream(settings.model_default_name, messages):
                if chunk:
                    yield chunk
        except Exception:
            if model_profile is not None or not settings.model_fallback_to_mock or isinstance(provider, MockModelProvider):
                raise
            async for chunk in MockModelProvider().stream(settings.model_default_name, messages):
                if chunk:
                    yield chunk
