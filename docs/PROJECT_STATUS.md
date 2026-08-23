# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**进行中**。
- 2.3-A Provider Governance Contract：**已实现并进入运行时强制执行**。
- 2.3-B Backend Domain + API Contract：**已实现**。
- 2.3-C Runtime Governance Invocation：**已实现并接入 WorkflowRuntime**。
- 2.3-D Runtime Usage / Trace Identity：**已实现基础能力**。
- 2.3-E Governed fallback success + deterministic multi-provider：**已通过开发者本地 Real API Gate**。
- 2.3-F Fallback Policy Enforcement：**已实现，待本地 targeted regression 验证**。

## 本轮实际验收证据

开发者在最新 `main`（`d0b7a2e`）实际执行并反馈：

```text
Targeted runtime governance tests: 30 passed
Backend default regression: 348 passed, 34 deselected
Alembic upgrade head: passed
Tenant Safe Real API Gate: 34 passed
```

因此 2.3-E 的 Real API acceptance blocker 已关闭。此前 `fallback_reason=connectivity` / actual `timeout` 不一致已修复，并进一步补齐了 HTTPX write/pool timeout 分类测试。

注意：上述结果对应 `d0b7a2e`。后续提交 `dd037f8` 新增了 FallbackPolicy 强制执行与对应单元测试，因此该新变更尚未由开发者本地执行，不能把它计入当前 Passed 数字。

## 当前 Runtime Governance 实现

Runtime 主链路现在：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 只接受治理 Contract 定义的 connectivity / timeout / rate limit / provider 5xx；
8. fallback attempt 数量受 `FallbackPolicy.max_attempts` 上限约束，当前最大值为 2；
9. `FallbackPolicy.enabled` 与 `eligible_reasons` 现在实际控制 Runtime fallback，而不是仅停留在 Contract；
10. 不允许静默 Mock fallback；
11. 每次 provider attempt 生成独立 `request_id`，并通过 Workflow Trace 记录 usage identity。

## 当前执行任务

**2.3-F Fallback Policy Enforcement**：将 2.3-A 中已定义的 fallback policy 从数据结构提升为 Runtime 强制规则，确保 enabled、eligible reasons、最大 attempts 在执行层真实生效。

已提交：`dd037f8` (`fix(runtime): enforce governed fallback policy`)

### 下一步

1. 开发者本地执行 2.3-F targeted tests；
2. 执行 Backend default regression；
3. 执行 Migration/head verification；
4. 执行 Tenant Safe Real API Gate；
5. 若全部通过，更新 Phase 2.3 Acceptance 并进入下一项尚未实现的 Cost / Usage accounting 能力；
6. Cost / Usage 若需要持久化，必须先新增 Alembic Migration，再实现依赖数据库结构的业务代码。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
