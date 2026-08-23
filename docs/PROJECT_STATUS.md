# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.3-A 至 2.3-G：**均已完成对应本地验收**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first 实现中；尚未进入 Migration / Scheduler Runtime 业务实现**。
- 下一正式工作：**完成 Phase 2.4 Contract Gate，然后进入 Backend Domain + API Contract**。

## Phase 2.3 最终本地验收结果

开发者在 `main` 最新基线实际执行：

```text
Targeted usage/governance tests: 40 passed
Backend Regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Alembic current: 0023_model_usage_accounting (head), 0027_retrieval_evaluation_vector_space (head)
Tenant Safe Real API Gate: 35 passed
```

以上结果来自开发者本地实际执行，不使用 GitHub Actions 作为开发测试、质量门禁或验收依据。

## Phase 2.3 交付结果

Runtime 已形成完整 Provider Governance：

1. 使用已发布 `AgentVersion.model_profile_id` 或 organization default；
2. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
3. 通过 `RuntimeModelGovernanceService` 从真实 PostgreSQL Provider/Profile 数据解析模型调用；
4. `FallbackPolicy` 强制控制 connectivity / timeout / rate limit / provider 5xx fallback，最大 attempts=2；
5. 禁止静默 Mock fallback；
6. provider attempt 具有独立 `request_id`，并通过 Workflow Trace 记录 usage identity；
7. `model_usage_records` 持久化 provider attempt、usage、pricing source/version 与成本；
8. usage 查询严格执行 active organization membership tenant scope；
9. endpoint、credential_ref、Token、Secret 不进入 usage/audit/trace。

## Phase 2.4 优先级与灵活性评估结论

**确认 Phase 2.4 Durable Scheduler 为下一项 P1 正式工作，采用 Contract-first、MVP 边界和可替换实现。**

### 为什么优先

当前平台已经具备 Workflow、Execution、Scheduled Trigger、Reliability、Audit/Trace 与 PostgreSQL 持久化基础。Durable Scheduler 能直接补齐现有 Scheduled Trigger 的长期运行可靠性，复用现有领域模型，实施范围和验收边界均明显小于 Advanced Workflow、Event Infrastructure、Multi-Agent 和 Marketplace。

因此当前优先级确定为：

```text
P1  Phase 2.4 Durable Scheduler
        ↓
P1  Phase 2.5 Advanced Workflow Orchestration
        ↓
P2  Phase 2.6 Enterprise Event Infrastructure
        ↓
P2  Phase 2.7 Multi-Agent Collaboration
        ↓
P2  Phase 2.8 Agent Asset / Marketplace
```

### 灵活性原则

Phase 2.4 首版只解决：持久化调度、`next_run_at`、多实例 lease、misfire、幂等、状态转换和 Audit/Trace。

暂不引入 MQ/Kafka、Temporal、独立 Scheduler 服务、跨区域调度、复杂 DAG 或通用任务平台。租约优先采用 PostgreSQL 原子更新/行锁，只有真实吞吐或可靠性数据证明不足时才单独评估基础设施升级。

## Phase 2.4 Contract-first 当前进度

已完成第一步纯领域 Contract 实现：

- `backend/app/services/workflow_scheduler_contract.py`：定义状态、misfire、时间、lease、slot 幂等键与可注入 clock 边界；
- `backend/tests/unit/test_workflow_scheduler_contract.py`：覆盖 UTC、IANA timezone、DST、lease、misfire、状态与幂等边界；
- 当前实现不访问 PostgreSQL、不创建 WorkflowExecution、不启动 scheduler worker，因此没有越过业务代码 Gate。

当前未宣称通过 Phase 2.4 Acceptance。下一步必须完成 Contract Gate 的完整确认后，再创建 Migration / API / Runtime 实现。

## Phase 2.4 Contract 进入条件

正式创建 Migration 或业务代码前必须确认：

1. `next_run_at` 的计算、时区与时钟语义；
2. 多实例 scheduler lease / ownership；
3. lease 过期、抢占与重复执行边界；
4. misfire policy 与可接受延迟；
5. 调度槽位幂等键与重复触发语义；
6. paused / enabled / disabled 状态转换；
7. 调度状态与 WorkflowExecution 的 Audit / Trace 关系；
8. PostgreSQL migration 与 Real API acceptance 场景。

Contract 确认后，按开发准则执行：

```text
Backend Domain + API Contract
        ↓
PostgreSQL Migration + Backend tests
        ↓
Real API Gate
        ↓
Backend Regression Gate
        ↓
Frontend API / UI（如存在明确用户操作范围）
        ↓
Browser E2E（如存在对应 UI 用户链路）
```

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码、Phase、Acceptance、Error、Status 必须保持可追溯。
- 代码中的功能说明和注释统一使用中文；技术标识保持原文。
