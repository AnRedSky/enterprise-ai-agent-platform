# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-G Circuit Breaker Real API 边界验收
- 当前角色：开发执行
- 当前 main 基线：`172728f916029cb589ee2519e83ba9fc85617b3f`
- 最新 main 提交：`fix: count only transient failures toward circuit threshold`

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
| Phase 1.5-F | 已完成 | Cancel / Retry / Retry lineage / Idempotency-Key / Execution Concurrency / Timeout / Failure Recovery / Node Retry / Attempt 治理已完成并进入后续可靠性收口 |
| Phase 1.5-G | 开发中 | Circuit Breaker 已落地 main，当前执行 Real API 边界验收 |
| 测试基础设施治理 | 持续治理 | Unit / Integration / API Contract / Real API 四层规范持续执行，不新增重复测试入口或混用开发/测试脚本 |

## 3. 强制测试链

```text
Unit → Integration → API Contract → Real API → Frontend Test/Build → Browser 联调
```

Real API 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

联调唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

禁止手工填写 `ACCESS_TOKEN`、`WORKFLOW_ID`、`WORKFLOW_EXECUTION_ID` 作为 Real API 测试前置条件。

## 4. 已验收基线

### Backend / Retry Reliability

开发者此前已反馈 Workflow Runtime Timeout / Failure Recovery、Node Retry / Attempt、Retry Budget、Retry Deadline 等链路测试全部通过。

### Migration

此前稳定 head：

```text
0019_workflow_execution_idempotency
```

Phase 1.5-G 新增：

```text
0020_workflow_circuit_breaker
```

该 migration 已提交到 main，必须由开发者本地实际执行 `uv run alembic upgrade head` 后才可标记验收通过。

### Real API

此前 Retry Governance Real API 边界已通过开发者反馈。

Phase 1.5-G Circuit Breaker Real API 尚未宣称通过，必须重新执行当前强制 Real API Gate。

### Frontend

此前 Frontend tests 与 production build 均通过；Phase 1.5-G 无独立 Circuit Breaker UI，但仍需执行前端测试与 production build 作为阶段门禁。

## 5. Phase 1.5-G Circuit Breaker 当前实现

已提交 main：

1. `WorkflowCircuitState` 持久化模型。
2. `0020_workflow_circuit_breaker` Alembic migration。
3. Database-backed `CircuitBreakerService`。
4. CLOSED / OPEN / HALF_OPEN 状态机。
5. `tenant_id + circuit_key` 隔离。
6. Circuit 状态读取与更新使用数据库行锁。
7. `failure_threshold`、`recovery_timeout_ms`、`half_open_max_calls` 配置校验。
8. OPEN 状态 Fast-Fail。
9. HALF_OPEN 探活槽位限制。
10. Workflow Runtime 集成 Circuit Breaker。
11. 仅 transient failure 计入熔断阈值；404 / 403 / 422 等业务/权限类错误不应触发熔断。
12. Circuit Breaker Unit Test 与 Runtime Contract Test。

设计原则与项目架构中的 `Timeout + Retry + Circuit Breaker` 容错要求一致；熔断状态外置到 PostgreSQL，保持 Runtime worker 无状态并支持多副本共享状态。

## 6. Phase 1.5-G 验收要求

Real API 必须覆盖：

1. Circuit disabled 保持既有 Runtime 行为。
2. transient failure 达到 threshold 后 CLOSED → OPEN。
3. OPEN 请求立即 Fast-Fail，不再次调用 Provider。
4. non-transient failure 不计入 failure count。
5. recovery timeout 后 OPEN → HALF_OPEN。
6. HALF_OPEN probe 数量受 `half_open_max_calls` 限制。
7. probe success 后 HALF_OPEN → CLOSED。
8. probe failure 后重新 OPEN。
9. Tenant isolation：不同 Tenant 的同名 circuit key 相互隔离。
10. Circuit OPEN 不错误消耗 Retry budget。
11. Circuit 与 Workflow Deadline / Retry 边界不互相绕过。
12. Execution / Node / Trace / Audit 最终状态一致。

## 7. 本轮必须执行

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
cd ..\frontend
npm test
npm run build
cd ..\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

实际测试结果必须以开发者反馈为准；当前不预填 Phase 1.5-G 的“通过”。

## 8. 下一步

**当前唯一优先工作项：Phase 1.5-G Circuit Breaker Real API 边界验收。**

完成并通过全部门禁后：

1. 更新本文件收口 Phase 1.5-G。
2. 更新 `docs/14-phase-1.5-g-circuit-breaker.md` 的实际验收结果。
3. 进入 Workflow Execution 查询列表与历史执行治理。
4. 再进入异步 Worker / 调度能力。
