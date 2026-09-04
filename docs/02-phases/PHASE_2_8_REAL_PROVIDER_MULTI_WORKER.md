# Phase 2.8 Worker / Delegation 多实例真实 Provider 验收补强

## 1. 背景

Phase 2.8 B6 已完成 Durable Frontier 多 Worker Claim、Lease、Workflow Execution 与 Delegation terminalization 的真实验收，但既有 Real API Gate 为避免外部模型 Provider 不可控，明确将 Delegation Fixture 绑定到组织内 Mock Provider。

本补强任务只针对该验收边界，不重新实现 Worker、Delegation、Runtime 或 Provider。

## 2. 根因审查结论

生产链路已经具备真实 Provider 能力：

```text
AgentVersion.model_profile_id
        ↓
AgentDelegation.model_profile_id
        ↓
AgentDelegationRuntimeBridge
        ↓
WorkflowRuntime.execute_node
        ↓
RuntimeModelGovernanceService
        ↓
ModelProviderService.resolve_routing
        ↓
ModelGateway.generate
        ↓
OpenAICompatibleProvider / Ollama-compatible Provider
```

关键事实：

1. Delegation 创建时复制 Target Agent published version 的 `model_profile_id`。
2. Worker Runtime 不复制 Provider；Delegation 进入唯一 `execute_claimed_execution` Runtime Entry。
3. Workflow Runtime 通过 Model Governance 根据 tenant / organization / explicit profile 解析 Provider/Profile。
4. Model Gateway 根据 Provider 类型构造 OpenAI-compatible Provider，并从 `credential_ref` 指向的环境变量读取凭据。
5. 因此没有发现“多 Worker 无法调用真实 Provider”的生产代码根因，不应为了补齐验收而新增第二套 Provider 或 Worker Runtime。

真正缺口是：既有 B6 Gate 的 Fixture 被刻意绑定到 Mock Provider，导致“多个独立 Worker + PostgreSQL Durable Frontier + 真实外部 Provider”这一组合事实没有验收证据。

## 3. 实施

新增：

- `backend/tests/api_real/test_agent_delegation_multi_worker_real_provider.py`
- `backend/scripts/test/phase-2.8/07_delegation_multi_worker_real_provider_gate.ps1`

测试生成完整 Tenant/API identity、Agent、Workflow、Execution、Delegation、Model Provider、Model Profile 数据，不要求手工填写业务 ID。

真实 Provider endpoint、model 与 credential ref 只能通过未提交环境配置提供：

```text
DELEGATION_REAL_PROVIDER_ENDPOINT
DELEGATION_REAL_PROVIDER_MODEL
DELEGATION_REAL_PROVIDER_TYPE        # openai-compatible / ollama，可选
DELEGATION_REAL_PROVIDER_API_KEY_ENV # 可选，值为环境变量名称而不是 Secret 本身
```

Secret 不进入 Git。

## 4. 验收范围

Real Provider 多 Worker 验收要求：

1. PostgreSQL 已升级到 Alembic head；
2. API、PostgreSQL、Redis 已由开发者预先启动；Gate 不启动或停止服务；
3. 不存在后台 Worker / Scheduler 消费者；
4. 两个独立 `WorkflowWorker` 实例竞争多个 Delegation Durable Frontier；
5. 每个 Delegation 使用持久化的真实 Model Profile；
6. Provider 类型为 `openai-compatible` 或 `ollama`；
7. Worker Runtime 真实调用外部 Provider；
8. PostgreSQL 最终存在 Delegation completed、Worker Execution completed、Frontier completed 三层事实；
9. Worker 与 Frontier ownership 最终释放；
10. 不允许回退 Mock Provider。

## 5. Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\07_delegation_multi_worker_real_provider_gate.ps1
```

本地执行结果必须以开发者实际输出为准；当前提交只代表代码与 Gate 已建立，不预填通过结论。

## 6. 完成条件

```text
Targeted Unit
    ↓
Alembic upgrade head / head verification
    ↓
Existing Delegation PostgreSQL Acceptance
    ↓
Two independent Workers
    ↓
Real Provider HTTP call
    ↓
Delegation / Execution / Frontier PostgreSQL facts
    ↓
Service boundary verification
```

通过后才关闭“Worker / Delegation 多实例真实 Provider 能力缺口”。
