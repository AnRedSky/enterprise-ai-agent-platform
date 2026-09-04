"""Workflow Runtime 编排模块。

模块职责：执行已发布 Workflow Definition 的顺序节点、DAG Resume frontier、条件分支、超时、重试、熔断与模型治理调用。
边界：不实现模型 Provider 或模型路由规则；模型调用统一通过 runtime.model.ModelGateway 和 services.model 治理服务；DAG Branch 状态与完成事实由 Planner / Executor Contract 提供。
关键依赖：SQLAlchemy AsyncSession、WorkflowExecutionService、CircuitBreakerService、DAG Planner / Executor 与 ModelProviderRoutingRequest。
"""

from __future__ import annotations

import asyncio
import random
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Agent, AgentVersion, User
from app.models.organization import Organization
from app.models.workflow_execution import WorkflowNodeExecution
from app.runtime.model import ModelGateway
from app.runtime.workflow.circuit_breaker import CircuitBreakerService, CircuitOpenError
from app.schemas.model_provider import ModelProviderRoutingRequest
from app.services.model import RuntimeModelGovernanceService
from app.services.workflow.checkpoint import WorkflowExecutionCheckpointService
from app.services.workflow.checkpoint.recovery.dag_executor import WorkflowDagMultiFrontierExecutor
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlanner
from app.services.workflow.checkpoint.recovery.dag_state_merge import WorkflowDagBranchState, WorkflowDagBranchStateMergeService


class WorkflowRuntime:
    """Workflow 执行运行时，统一编排节点、DAG、重试、超时与模型治理。"""

    NODE_TYPES = {"input", "agent", "output"}
    DEFAULT_TIMEOUT_MS = 30_000
    MAX_TIMEOUT_MS = 300_000
    DEFAULT_RETRY_POLICY = {
        "max_attempts": 1,
        "backoff_ms": 250,
        "max_backoff_ms": 5_000,
        "jitter_ms": 250,
        "retryable_error_codes": ["NODE_TIMEOUT", "HTTP_429", "HTTP_502", "HTTP_503", "HTTP_504", "CONNECTION_ERROR"],
    }
    CIRCUIT_FAILURE_CODES = {"NODE_TIMEOUT", "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504", "CONNECTION_ERROR"}

    def __init__(self, db: AsyncSession, execution_service=None):
        self.db = db
        self.gateway = ModelGateway()
        self.governance = RuntimeModelGovernanceService(db, gateway=self.gateway)
        self.circuit_breaker = CircuitBreakerService(db)
        self.execution_service = execution_service

    @classmethod
    def validate_timeout_ms(cls, value: object, *, field: str = "timeout_ms") -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(422, f"{field} 必须为整数毫秒")
        if value <= 0 or value > cls.MAX_TIMEOUT_MS:
            raise HTTPException(422, f"{field} 必须在 1-{cls.MAX_TIMEOUT_MS} 毫秒范围内")
        return value

    @classmethod
    def resolve_timeout_ms(cls, config: dict | None, *, field: str = "timeout_ms") -> int:
        return cls.validate_timeout_ms((config or {}).get(field, cls.DEFAULT_TIMEOUT_MS), field=field)

    @classmethod
    def resolve_retry_policy(cls, config: dict | None) -> dict:
        raw = (config or {}).get("retry") or {}
        if not isinstance(raw, dict):
            raise HTTPException(422, "retry config 必须为对象")
        policy = {**cls.DEFAULT_RETRY_POLICY, **raw}
        max_attempts = policy["max_attempts"]
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 5:
            raise HTTPException(422, "retry.max_attempts 必须在 1-5 范围内")
        for key, maximum in (("backoff_ms", 10_000), ("max_backoff_ms", 60_000), ("jitter_ms", 10_000)):
            value = policy[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
                raise HTTPException(422, f"retry.{key} 必须在 0-{maximum} 毫秒范围内")
        if policy["max_backoff_ms"] < policy["backoff_ms"]:
            raise HTTPException(422, "retry.max_backoff_ms 不能小于 retry.backoff_ms")
        codes = policy["retryable_error_codes"]
        if not isinstance(codes, list) or any(not isinstance(code, str) or not code for code in codes):
            raise HTTPException(422, "retry.retryable_error_codes 必须为非空字符串数组")
        return {"max_attempts": max_attempts, "backoff_ms": policy["backoff_ms"], "max_backoff_ms": policy["max_backoff_ms"], "jitter_ms": policy["jitter_ms"], "retryable_error_codes": list(dict.fromkeys(codes))}

    @classmethod
    def resolve_circuit_breaker(cls, config: dict | None) -> dict:
        return CircuitBreakerService.validate_config(config)

    @classmethod
    def classify_error(cls, exc: BaseException, *, workflow_timeout: bool = False) -> str:
        if workflow_timeout:
            return "WORKFLOW_TIMEOUT"
        if isinstance(exc, CircuitOpenError):
            return "CIRCUIT_OPEN"
        if isinstance(exc, asyncio.TimeoutError):
            return "NODE_TIMEOUT"
        if isinstance(exc, HTTPException):
            return f"HTTP_{exc.status_code}"
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return "CONNECTION_ERROR" if isinstance(exc, ConnectionError) else "NODE_TIMEOUT"
        return type(exc).__name__

    @classmethod
    def retry_delay_seconds(cls, policy: dict, failed_attempt: int, random_value: float) -> float:
        ceiling_ms = min(policy["max_backoff_ms"], policy["backoff_ms"] * (2 ** max(failed_attempt - 1, 0)))
        jitter_ms = max(0.0, min(1.0, random_value)) * policy["jitter_ms"]
        return min(policy["max_backoff_ms"], ceiling_ms + jitter_ms) / 1000

    @classmethod
    def validate_definition(cls, definition: dict, *, allow_legacy_empty_nodes: bool = False) -> list[dict]:
        """校验 Workflow Definition，并在明确授权时兼容历史空节点版本。"""
        if not isinstance(definition, dict):
            raise HTTPException(422, "Workflow definition 必须为对象")
        nodes = definition.get("nodes")
        if not isinstance(nodes, list):
            raise HTTPException(422, "Workflow definition 必须包含 nodes 数组")
        if not nodes and not allow_legacy_empty_nodes:
            raise HTTPException(422, "Workflow definition 必须包含非空 nodes")
        runtime_config = definition.get("config") or {}
        if not isinstance(runtime_config, dict):
            raise HTTPException(422, "Workflow config 必须为对象")
        cls.resolve_timeout_ms(runtime_config)
        cls.resolve_circuit_breaker(runtime_config)
        seen: set[str] = set()
        normalized: list[dict] = []
        for raw in nodes:
            if not isinstance(raw, dict):
                raise HTTPException(422, "Workflow node 必须为对象")
            node_id = raw.get("id")
            node_type = raw.get("type")
            if not isinstance(node_id, str) or not node_id or len(node_id) > 100:
                raise HTTPException(422, "Workflow node id 无效")
            if node_id in seen:
                raise HTTPException(422, f"Workflow node id 重复: {node_id}")
            if node_type not in cls.NODE_TYPES:
                raise HTTPException(422, f"不支持的 Workflow node type: {node_type}")
            config = raw.get("config") or {}
            if not isinstance(config, dict):
                raise HTTPException(422, f"Workflow node config 必须为对象: {node_id}")
            cls.resolve_timeout_ms(config)
            cls.resolve_retry_policy(config)
            cls.resolve_circuit_breaker(config)
            seen.add(node_id)
            normalized.append({"id": node_id, "type": node_type, "config": config})
        return normalized

    async def _load_completed_resume_nodes(self, execution) -> list[WorkflowNodeExecution]:
        """读取当前 Execution 及 Resume Source 的已完成 Node 事实，并严格限制在当前租户边界内。"""
        execution_ids = [execution.id]
        source_execution_id = getattr(execution, "resume_of_execution_id", None)
        if source_execution_id is not None:
            execution_ids.insert(0, source_execution_id)
        query = select(WorkflowNodeExecution).where(
            WorkflowNodeExecution.execution_id.in_(execution_ids),
            WorkflowNodeExecution.tenant_id == execution.tenant_id,
            WorkflowNodeExecution.status == "completed",
        ).order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
        return list((await self.db.execute(query)).scalars().all())

    @staticmethod
    def _build_frontier_branch_states(
        definition: dict,
        frontier_node_ids: tuple[str, ...],
        source_nodes: list[WorkflowNodeExecution],
        selected_predecessor_node_ids: tuple[tuple[str, tuple[str, ...]], ...] = (),
    ) -> dict[str, dict]:
        """从已完成 predecessor 输出构造当前 frontier 的独立 Branch state。"""
        source_by_id: dict[str, dict] = {}
        for node in source_nodes:
            source_by_id[node.node_id] = dict(node.output_data or {})
        all_predecessors = {node["id"]: [] for node in definition.get("nodes", []) if isinstance(node, dict) and isinstance(node.get("id"), str)}
        for edge in definition.get("edges", []) or []:
            if isinstance(edge, dict) and edge.get("target") in all_predecessors:
                all_predecessors[edge["target"]].append(edge.get("source"))
        selected_map = dict(selected_predecessor_node_ids)
        result: dict[str, dict] = {}
        for node_id in frontier_node_ids:
            predecessor_ids = list(selected_map.get(node_id, tuple(all_predecessors.get(node_id, []))))
            states = []
            for predecessor_id in predecessor_ids:
                if predecessor_id not in source_by_id:
                    raise ValueError(f"DAG Resume frontier {node_id} 缺少已完成 predecessor state")
                states.append(source_by_id[predecessor_id])
            if not states:
                raise ValueError(f"DAG Resume frontier {node_id} 缺少已完成 predecessor state")
            if len(states) == 1:
                result[node_id] = states[0]
            else:
                result[node_id] = WorkflowDagBranchStateMergeService.merge(tuple(
                    WorkflowDagBranchState(node_id=f"{node_id}:predecessor:{index}", state_data=state)
                    for index, state in enumerate(states)
                )).state_data
        return result

    async def _resolve_dag_context(self, execution, definition: dict, state_data: dict):
        """根据当前持久化 Node 完成事实计算初始执行或 Resume 的 DAG frontier。"""
        if not definition.get("edges"):
            return None
        source_nodes = await self._load_completed_resume_nodes(execution)
        completed_node_ids = {node.node_id for node in source_nodes}
        state_data_by_node = {node.node_id: dict(node.output_data or {}) for node in source_nodes}
        try:
            plan = WorkflowDagResumePlanner.plan(
                definition=definition,
                completed_node_ids=completed_node_ids,
                state_data_by_node=state_data_by_node,
            )
            branch_state_data = self._build_frontier_branch_states(
                definition,
                plan.frontier_node_ids,
                source_nodes,
                plan.selected_predecessor_node_ids,
            ) if plan.frontier_node_ids and completed_node_ids else {}
            runtime_plan = WorkflowDagResumeRuntimePlanner.plan(
                definition=definition,
                completed_node_ids=completed_node_ids,
                state_data=state_data,
                branch_state_data=branch_state_data if len(plan.frontier_node_ids) > 1 else None,
                state_data_by_node=state_data_by_node,
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return runtime_plan, branch_state_data

    async def _resolve_resume_context(self, execution, definition: dict, state_data: dict):
        """根据持久化完成事实计算当前 Resume frontier 与独立 Branch state。"""
        if getattr(execution, "resume_of_execution_id", None) is None:
            return None
        return await self._resolve_dag_context(execution, definition, state_data)

    async def _execute_node_with_policy(self, service, execution, node: dict, current_data: dict, actor_id: UUID,
                                        is_admin: bool, workflow_timeout: int, max_retries: int, started: float,
                                        workflow_retry_counter: list[int]) -> dict:
        """执行单个 Node，并复用既有 Retry、ownership、NodeExecution 与 Checkpoint Contract。"""
        policy = self.resolve_retry_policy(node["config"])
        attempt = 0
        while True:
            attempt += 1
            remaining = workflow_timeout / 1000 - (asyncio.get_running_loop().time() - started)
            if remaining <= 0:
                await service.transition_node(execution, node["id"], "failed", input_data=current_data, error_code="WORKFLOW_TIMEOUT", error_message="Workflow deadline exceeded", commit=False)
                raise HTTPException(504, "Workflow deadline exceeded")
            await service.transition_node(execution, node["id"], "running", input_data=current_data, commit=False)
            node_timeout = self.resolve_timeout_ms(node["config"])
            timeout_seconds = min(node_timeout / 1000, remaining)
            deadline_limited = remaining <= node_timeout / 1000
            try:
                output = await asyncio.wait_for(self.execute_node(node, current_data, actor_id, is_admin, execution.id, execution.tenant_id, execution=execution), timeout=timeout_seconds)
                await service.transition_node(execution, node["id"], "completed", output_data=output, commit=False)
                return output
            except asyncio.TimeoutError as exc:
                failure: BaseException = exc
                error_code = self.classify_error(exc, workflow_timeout=deadline_limited)
                error_message = "Workflow deadline exceeded" if deadline_limited else "Workflow node timeout"
            except Exception as exc:
                failure = exc
                error_code = self.classify_error(exc)
                error_message = str(exc)
            await service.transition_node(execution, node["id"], "failed", input_data=current_data, error_code=error_code, error_message=error_message, commit=False)
            retryable = error_code in policy["retryable_error_codes"] and error_code not in {"CIRCUIT_OPEN", "WORKFLOW_TIMEOUT"}
            if not retryable or attempt >= policy["max_attempts"] or workflow_retry_counter[0] >= max_retries:
                if error_code == "WORKFLOW_TIMEOUT":
                    raise HTTPException(504, error_message)
                if error_code.startswith("HTTP_"):
                    raise failure if isinstance(failure, HTTPException) else HTTPException(int(error_code.split("_", 1)[1]), error_message)
                if error_code == "CIRCUIT_OPEN":
                    raise CircuitOpenError(node["id"])
                if error_code == "NODE_TIMEOUT":
                    raise HTTPException(504, error_message)
                if error_code == "CONNECTION_ERROR":
                    raise failure if isinstance(failure, ConnectionError) else ConnectionError(error_message)
                raise HTTPException(500, error_message)
            delay = self.retry_delay_seconds(policy, attempt, random.random())
            remaining = workflow_timeout / 1000 - (asyncio.get_running_loop().time() - started)
            if delay > remaining:
                raise HTTPException(504, "Retry backoff exceeds workflow deadline")
            workflow_retry_counter[0] += 1
            await service.governance.audit(execution, actor_id, "workflow.node.retry", "scheduled", error_code=error_code, metadata={"node_id": node["id"], "attempt": attempt + 1, "delay_ms": int(delay * 1000)})
            await asyncio.sleep(delay)

    async def _execute_multi_frontier(self, service, execution, plan, branch_state_data, actor_id, is_admin,
                                      workflow_timeout, max_retries, started, workflow_retry_counter):
        """执行当前 Multi-frontier，并在全部 Branch Node Fact 成功后写入 Execution-level frontier checkpoint。"""
        async def execute_branch(node, input_data):
            return await self._execute_node_with_policy(service, execution, node, input_data, actor_id, is_admin, workflow_timeout, max_retries, started, workflow_retry_counter)

        async def checkpoint_branch(node_id, output):
            if not isinstance(output, dict):
                raise ValueError(f"DAG frontier Node {node_id} Checkpoint state 必须为对象")

        result = await WorkflowDagMultiFrontierExecutor.execute(
            plan,
            branch_state_data=branch_state_data,
            executor=execute_branch,
            checkpoint_writer=checkpoint_branch,
        )
        if not result.join_ready:
            return result
        checkpoint = WorkflowExecutionCheckpointService(self.db)
        await checkpoint.append_next_in_transaction(
            execution_id=execution.id,
            execution_status=execution.status,
            state_data=dict(result.merged_state_data or {}),
            checkpoint_reason="frontier_completed",
            worker_owner=execution.worker_owner,
            expected_worker_owner=execution.worker_owner,
            expected_worker_attempt=int(execution.worker_attempt or 0),
            tenant_id=execution.tenant_id,
        )
        return result

    async def execute(self, execution, version, actor_id: UUID, is_admin: bool = False,
                      allow_legacy_empty_nodes: bool = False, *, commit: bool = True) -> dict:
        """执行 Workflow，并由调用方控制终态提交边界；commit=False 时禁止 Runtime 提前提交。"""
        if self.execution_service is None:
            from app.services.workflow import WorkflowExecutionService
            service = WorkflowExecutionService(self.db)
        else:
            service = self.execution_service
        nodes = self.validate_definition(version.definition, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        runtime_config = version.definition.get("config") or {}
        workflow_timeout = self.resolve_timeout_ms(runtime_config)
        retry_budget = runtime_config.get("retry_budget") or {}
        if not isinstance(retry_budget, dict):
            raise HTTPException(422, "retry_budget config 必须为对象")
        max_retries = retry_budget.get("max_retries", 0)
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0 or max_retries > 20:
            raise HTTPException(422, "retry_budget.max_retries 必须在 0-20 范围内")
        current_data = dict(execution.input_data or {})
        started = asyncio.get_running_loop().time()
        workflow_retry_counter = [0]

        dag_context = await self._resolve_dag_context(execution, version.definition, current_data)
        if dag_context is not None:
            plan, branch_state_data = dag_context
            while plan.frontier_node_ids:
                if len(plan.frontier_node_ids) > 1:
                    result = await self._execute_multi_frontier(service, execution, plan, branch_state_data, actor_id, is_admin, workflow_timeout, max_retries, started, workflow_retry_counter)
                    if not result.join_ready:
                        raise HTTPException(409, "DAG Multi-frontier Branch 尚未全部完成，Join 不可就绪")
                    current_data = result.merged_state_data or {}
                else:
                    node = plan.nodes[0]
                    current_data = await self._execute_node_with_policy(service, execution, node, branch_state_data.get(plan.frontier_node_ids[0], current_data), actor_id, is_admin, workflow_timeout, max_retries, started, workflow_retry_counter)
                dag_context = await self._resolve_dag_context(execution, version.definition, current_data)
                if dag_context is None:
                    break
                plan, branch_state_data = dag_context
            await service.transition(execution, "completed", output_data=current_data, actor_id=actor_id, commit=commit)
            return current_data

        for node in nodes:
            current_data = await self._execute_node_with_policy(service, execution, node, current_data, actor_id, is_admin, workflow_timeout, max_retries, started, workflow_retry_counter)
        await service.transition(execution, "completed", output_data=current_data, actor_id=actor_id, commit=commit)
        return current_data

    async def _resolve_organization_id(self, tenant_id: UUID | None) -> UUID:
        if tenant_id is None:
            raise HTTPException(409, "Workflow Runtime 缺少 organization scope")
        organization_id = (await self.db.execute(select(Organization.id).where(Organization.tenant_id == tenant_id, Organization.status == "active"))).scalar_one_or_none()
        if organization_id is None:
            raise HTTPException(409, "Workflow Runtime 所属 Organization 不存在或未启用")
        return organization_id

    @staticmethod
    def _governance_request(config: dict, organization_id: UUID, model_profile_id: UUID | None) -> ModelProviderRoutingRequest:
        governance = config.get("model_governance") or {}
        if not isinstance(governance, dict):
            raise HTTPException(422, "model_governance config 必须为对象")
        required_capabilities = governance.get("required_capabilities") or []
        allowed_provider_ids = governance.get("allowed_provider_ids") or []
        if not isinstance(required_capabilities, list) or any(not isinstance(item, str) or not item for item in required_capabilities):
            raise HTTPException(422, "model_governance.required_capabilities 必须为字符串数组")
        try:
            allowed_provider_ids = [UUID(str(item)) for item in allowed_provider_ids]
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "model_governance.allowed_provider_ids 必须为 UUID 数组") from exc
        return ModelProviderRoutingRequest(organization_id=organization_id, model_type="chat", routing_strategy="explicit_profile" if model_profile_id is not None else "organization_default", profile_id=model_profile_id, required_capabilities=required_capabilities, allowed_provider_ids=allowed_provider_ids)

    async def execute_node(self, node: dict, input_data: dict, actor_id: UUID, is_admin: bool,
                           session_id: UUID, tenant_id: UUID | None = None, execution=None) -> dict:
        """执行单个 Workflow Node；不直接修改 Execution 状态或 Checkpoint。"""
        node_type = node["type"]
        config = node["config"]
        if node_type in {"input", "output"}:
            return dict(input_data)
        agent_id = config.get("agent_id")
        try:
            agent_uuid = UUID(str(agent_id))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "agent node 必须提供有效 agent_id") from exc
        agent_query = select(Agent).join(User, User.id == Agent.owner_id).where(Agent.id == agent_uuid)
        if tenant_id is not None:
            agent_query = agent_query.where(User.tenant_id == tenant_id)
        agent = (await self.db.execute(agent_query)).scalar_one_or_none()
        if agent is None:
            raise HTTPException(404, "Workflow Agent 不存在")
        if not is_admin and agent.owner_id != actor_id:
            raise HTTPException(403, "无权执行 Workflow Agent")
        if agent.status != "published" or not agent.published_version_id:
            raise HTTPException(409, "Workflow Agent 尚未发布可运行版本")
        version = (await self.db.execute(select(AgentVersion).where(AgentVersion.id == agent.published_version_id, AgentVersion.agent_id == agent.id))).scalar_one_or_none()
        if version is None:
            raise HTTPException(409, "Workflow Agent 发布版本不存在")
        prompt = config.get("prompt")
        if prompt is None:
            prompt = input_data.get("input", input_data.get("content", ""))
        if not isinstance(prompt, str) or not prompt:
            raise HTTPException(422, "agent node 输入必须提供 prompt 或 input/content")
        circuit_config = self.resolve_circuit_breaker(config)
        circuit_key = circuit_config.get("key") or f"agent:{agent.id}:model:{version.model_profile_id or version.model_id}"
        if not isinstance(circuit_key, str) or not circuit_key or len(circuit_key) > 200:
            raise HTTPException(422, "circuit_breaker.key 必须为 1-200 字符字符串")
        circuit_tenant_id = tenant_id
        circuit_state = "closed"
        if circuit_tenant_id is not None:
            circuit_state = await self.circuit_breaker.before_call(circuit_tenant_id, circuit_key, config)
        messages = [{"role": "system", "content": version.system_prompt}, {"role": "user", "content": prompt}]
        try:
            organization_id = await self._resolve_organization_id(tenant_id)
            governance_request = self._governance_request(config, organization_id, version.model_profile_id)
            async def on_governed_attempt(candidate, request_id, outcome, fallback_reason, result):
                if self.execution_service is None or execution is None:
                    return
                data = {"organization_id": str(organization_id), "provider_id": str(candidate.provider.id), "profile_id": str(candidate.profile.id), "model_type": candidate.profile.model_type, "request_id": request_id, "trace_id": str(execution.id), "outcome": outcome}
                if fallback_reason is not None:
                    data["fallback_reason"] = fallback_reason.value
                if result is not None and result.usage is not None:
                    data["usage"] = {"prompt_tokens": result.usage.prompt_tokens, "completion_tokens": result.usage.completion_tokens, "total_tokens": result.usage.total_tokens}
                await self.execution_service.governance.trace(execution, actor_id, "model.invocation", outcome, node_id=node["id"], data=data)
            result = await self.governance.invoke(governance_request, actor_id, messages, on_attempt=on_governed_attempt)
        except Exception as exc:
            if circuit_tenant_id is not None and self.classify_error(exc) in self.CIRCUIT_FAILURE_CODES:
                await self.circuit_breaker.record_failure(circuit_tenant_id, circuit_key, config)
                if circuit_state == "half_open":
                    raise CircuitOpenError(circuit_key) from exc
            raise
        if circuit_tenant_id is not None:
            await self.circuit_breaker.record_success(circuit_tenant_id, circuit_key, config)
        usage = result.usage
        return {"content": result.content, "model_id": result.model, "agent_id": str(agent.id), "agent_version": agent.published_version_id and version.version, "usage": {"prompt_tokens": usage.prompt_tokens if usage else None, "completion_tokens": usage.completion_tokens if usage else None, "total_tokens": usage.total_tokens if usage else None}}
