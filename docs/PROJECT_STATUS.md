# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT_GUIDELINES.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-F Workflow Runtime 执行治理闭环
- 当前角色：开发执行
- 基线：2026-08-20 远端 `main` 已完成 Workflow Registry / Version / Publish / Execution / Audit / Trace、Idempotency-Key、Execution 状态并发锁、Runtime Timeout / Failure Recovery Hardening 闭环

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5-A | 已完成 | Workflow Definition Contract，本地 Backend 验收通过 |
| Phase 1.5-B | 已完成 | Publish Governance、Tenant Contract，本地 Backend 手工验收通过 |
| Phase 1.5-C | 已完成 | Workflow Execution State Machine，本地 Backend 验收通过 |
| Phase 1.5-D | 已完成 | Workflow Runtime Integration；本地验收无异常 |
| Phase 1.5-E | 已完成 | Governance / Audit / Trace；全量测试通过，warning 已修复并验收通过 |
| Phase 1.5-F | 开发中 | Vue Workflow / Governance 管理端及 Runtime 执行治理；Cancel / Retry / Retry lineage / Idempotency-Key / Execution Concurrency / Timeout / Failure Recovery 已完成，当前进入 Node-level Retry / Attempt 治理 |
| 测试基础设施治理 | 持续治理 | 已建立 Unit / Integration / API Contract / Real API 四层规范，并迁移 API Contract、Real API 与联调入口；不新增重复测试入口或混用开发/测试脚本 |

## 3. 强制测试链

```text
Unit → Integration → API Contract → Real API → Frontend Test/Build → Browser 联调
```

Real API Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

统一联调 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

禁止手工填写 `ACCESS_TOKEN`、`WORKFLOW_ID`、`WORKFLOW_EXECUTION_ID` 作为 Real API 测试前置条件。

## 4. 已验收基线

### Backend regression

最近一次开发者反馈：

```text
全部通过
```

### Migration

最近一次开发者反馈：

```text
0019_workflow_execution_idempotency (head)
```

### Real API Gate

最近一次开发者反馈：

```text
5 passed
[PASS] Real API gate completed.
```

真实 HTTP 链路已覆盖：

```text
Register → Login → Workflow → Version → Publish → Execution → Audit → Trace
```

### Frontend

最近一次开发者反馈：Frontend tests 全部通过；production build 无 vendor circular chunk warning，也无 >500KB chunk warning。

## 5. Phase 1.5-F 当前实现

已完成：

1. Workflow Registry / Version / Publish 管理界面。
2. Workflow Definition JSON 编辑与新 Version 创建。
3. Workflow Audit 查询展示。
4. Workflow Trace 查询展示。
5. Workflow Execution / Node API types 与查询封装。
6. Governance 页面新增 Execution 状态、当前节点、时间、错误及 Node 状态展示。
7. Workflow API contract tests 与 Governance view tests。
8. Real API bootstrap 已改为自动发现/创建最小可执行 Workflow fixture，避免空 `nodes` definition 导致 422。
9. Execution Cancel：`pending/running → cancelled`，支持取消原因并写入 Audit / Trace。
10. Execution Retry：仅允许 `failed → new pending Execution`，不修改原 Execution。
11. Retry lineage：新增 `retry_of_execution_id`，新旧 Execution 可追溯关联。
12. Governance 页面新增 Cancel / Retry 操作及 Retry 来源展示。
13. Frontend Workflow API tests 增加 Cancel / Retry contract coverage。
14. Backend API contract tests 增加 Cancel / Retry route coverage。
15. Backend unit tests 增加 Cancel / Retry 状态治理测试。
16. Execution Idempotency-Key contract：通过 HTTP `Idempotency-Key` 请求头关联同 Tenant 的 Execution 创建请求。
17. Idempotency-Key 唯一约束：同 Tenant 下重复 Key 返回原 Execution；跨 Workflow / Version 重用返回 409；并处理并发插入竞争。
18. Idempotency 创建链路写入 Audit / Trace 时只记录 key 是否存在，不记录具体 key 值。
19. Frontend Workflow API 已支持可选 `Idempotency-Key`，并补充 API contract test。
20. Execution 状态转换新增数据库行锁：真实 `AsyncSession` 下使用 `SELECT ... FOR UPDATE` 重新读取 Execution，再进行状态校验和更新。
21. Cancel / Run / Retry / Node transition 不再依赖调用方持有的旧状态完成最终状态判定，降低并发操作下的 stale-state race window。
22. 新增 Execution row-locking unit coverage，验证 `FOR UPDATE` 与锁后状态重新校验。
23. Workflow Runtime 新增统一 timeout policy：Workflow / Node 均支持 `config.timeout_ms`，默认 30 秒，最大 300 秒。
24. Runtime 使用 `asyncio.wait_for` 对 Node 执行建立硬超时边界，Workflow 总 deadline 对多个 Node 的累计执行时间进行约束。
25. Node 超时统一落为 `NODE_TIMEOUT`，Workflow 总 deadline 超时统一落为 `WORKFLOW_TIMEOUT`，并将对应 Node / Execution 标记为 `failed`、写入 Audit / Trace。
26. Timeout 以 HTTP 504 向调用方暴露，不再将超时包装成普通 500；failed Execution 保持现有 Retry recovery 边界。
27. 新增 Workflow Runtime timeout policy、Node timeout、Workflow deadline timeout unit coverage。
28. Node retry policy 默认单次执行，只有显式配置 `retry.max_attempts > 1` 才启用自动重试，避免改变既有 Workflow 行为。
29. Retry policy 校验 `max_attempts`、指数退避、最大退避、jitter 与 retryable error code 白名单，并限制最大 attempt / delay，避免无限重试。
30. Retryable / non-retryable failure 分类：仅明确的超时、连接错误、429、502、503、504 等 transient error code 默认允许进入 retry policy；422、403、404 等业务/权限错误不会自动重试。
31. WorkflowNodeExecution 复用既有 `attempt` 字段记录当前 attempt；`failed → running` 仅作为内部 retry transition，并在重新运行时递增 attempt。
32. 每次 retry schedule 写入 Audit / Trace，记录 attempt、next attempt、delay、max attempts 与 error code，不记录敏感请求内容。
33. Retry delay 使用有上限的 exponential backoff + jitter，并受 Workflow 总 deadline 约束；若等待时间会越过 deadline，则终止为 `WORKFLOW_TIMEOUT`。
34. 新增 Node retry policy、error classification、bounded backoff 与 failed-node next-attempt unit coverage。

## 6. 本轮数据库变更

本轮 Node-level Retry / Attempt 治理**无数据库结构变更**，直接复用既有 `workflow_node_executions.attempt` 与 Workflow Trace / Audit 作为 attempt 治理与历史记录载体，不新增 migration。

既有数据库变更：

```text
0018_workflow_execution_retry_lineage
0019_workflow_execution_idempotency
```

0019 内容：

- `workflow_executions.idempotency_key`
- `(tenant_id, idempotency_key)` 唯一约束

## 7. 当前待验收

本轮 Node-level Retry / Attempt 治理代码已提交到 `phase-1-5-f-node-retry` 开发分支，尚未宣称本轮本地验收通过。开发者需要按强制测试链执行：

1. `cd backend && uv run pytest -q`
2. `cd backend && powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1`
3. `cd backend && powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1`
4. `cd frontend && npm test`
5. `cd frontend && npm run build`
6. 浏览器级验证 Workflow → Node transient failure → retry schedule → attempt 递增 → success / exhausted → Audit / Trace

特别验证：

- 未配置 `retry` 时仍只执行一次，不改变既有行为。
- `retry.max_attempts` 必须为 `1..5`。
- `retry.backoff_ms`、`retry.max_backoff_ms`、`retry.jitter_ms` 必须在受控范围内。
- `retry.max_backoff_ms >= retry.backoff_ms`。
- retryable error code 必须通过显式白名单判定，非 retryable 错误不得自动重试。
- Node 第一次失败后进入 retry schedule，下一次 `running` 时 `attempt` 从 1 增加到 2。
- 达到 `max_attempts` 后 Execution 保持 `failed`，不得继续重试。
- Retry delay 采用 exponential backoff + jitter，并且不得越过 Workflow deadline。
- Workflow deadline 被 retry delay 消耗时统一以 `WORKFLOW_TIMEOUT` 终止。
- 每个 retry schedule 必须存在对应 Audit / Trace，包含 attempt / delay / error code。
- 全量测试无新增 warning。
- Migration head 保持 `0019_workflow_execution_idempotency`。

## 8. 下一步

当前不继续人为拆分 vendor chunk，也不新增重复测试入口。

**当前工作项：Workflow Execution Reliability Hardening**

优先顺序：

1. Runtime 超时与失败恢复边界：已实现并已通过开发者验收。
2. **Node-level retry / attempt 治理：本轮已实现，待强制测试链验收。**
3. Execution 查询列表与历史执行治理。
4. 再进入更高阶段的 Workflow 调度与异步 Worker 能力。
