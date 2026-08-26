# Phase 2.6 — Durable Execution Checkpoint Foundation Acceptance

## 1. 验收目标

验证 WorkflowRuntime 的 Node completion 已形成真实 PostgreSQL Checkpoint 持久化边界：

```text
Worker / HTTP Runtime
        ↓
WorkflowExecutionService.transition_node(completed)
        ↓
Node state + Checkpoint append
        ↓
同一 PostgreSQL transaction commit
```

Checkpoint 不承担 Resume、调度或 ownership 决策。

## 2. 自动化入口

### Checkpoint targeted unit

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_checkpoint.py tests/unit/test_workflow_checkpoint_integration.py tests/unit/test_workflow_checkpoint_recovery.py
```

### Backend Regression

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

### Tenant Safe Real API

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

### Checkpoint Real PostgreSQL persistence

```powershell
cd backend
uv run pytest -q tests/api_real/test_workflow_checkpoint_api.py -m real_api
```

该测试要求预先准备 Real API、Worker 与 PostgreSQL；不会启动、停止或重启任何服务。正式验收优先使用 Tenant Safe Real API Gate。

## 3. Real API 源码基线前置

Tenant Safe Real API Gate 在实际执行测试前会运行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev\verify_real_api_source_baseline.ps1
```

该 Gate 必须确认：

```text
HEAD == origin/main
关键 Real API / Checkpoint 测试文件无未提交修改
Runtime Model Governance 测试使用统一 Worker claim race helper
```

这样可以避免旧工作树/旧测试实现把合法 Worker ownership race 误报为产品回归。

## 4. 服务版本前置

Checkpoint / Resume Candidate 是 API / Worker 进程内的 Python 代码。服务进程已经启动后再更新代码，旧进程不会自动载入新的实现。因此代码更新后必须人工重启受影响的 API Service 与 Worker Service，再执行 Real API Gate。

测试 Gate 本身禁止进行服务生命周期控制：

```text
代码更新
   ↓
人工重启 API Service
   ↓
人工重启 Worker Service
   ↓
Source Baseline Gate
   ↓
Real API / Backend Gate
```

推荐本地启动：

```powershell
# Terminal 1
uv run python run.py

# Terminal 2
uv run python run_worker.py
```

Scheduler 对本次 Checkpoint persistence gate 不是必需依赖，但现有 Scheduler 若继续运行可以保持不变；不得为了测试脚本自动重启 Scheduler。

## 5. 数据库前置

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

预期：

```text
0032_workflow_execution_checkpoint (head)
```

## 6. Node completion 断言

必须满足：

```text
Node running
    ↓
transition_node(..., completed)
    ↓
Checkpoint sequence = Execution 当前最大 sequence + 1
    ↓
Node + Checkpoint 同事务提交
```

禁止：

```text
Node committed
Checkpoint commit failed / missing
```

## 7. Real PostgreSQL 断言

Real API Checkpoint Gate 每轮都会新建一个 Execution 并立即执行，不再依赖 bootstrap 阶段历史 `WORKFLOW_EXECUTION_ID`，避免旧 Execution 污染验收结果。

真实 HTTP Execution 完成后，PostgreSQL 中必须存在：

```text
execution_id = 本轮新建 HTTP Execution ID
checkpoint_reason = node.completed
node_status = completed
sequence = 0..N 连续递增
```

测试必须读取真实 PostgreSQL，而不能使用 JSON fixture 或进程内 Mock 数据代替。

## 8. Worker claim race 断言

Real API 测试中独立 Worker 可以先于手动 `/run` claim 新建 Execution，此时 HTTP `/run` 返回 `409 只有 pending Execution 可以 Run` 属于合法 ownership race，而不是 Runtime 状态机错误。

测试必须统一通过 `run_or_observe_execution()`：

```text
POST /run
   ├── 200 / 业务预期状态 → 直接使用 HTTP 结果
   └── 409 pending claim race
         ↓
      GET Execution
         ↓
      等待真实 Worker 写入 terminal state
```

禁止在具体测试里复制第二套竞态处理逻辑，也禁止把生产 `running → running` 改为合法状态。

## 9. Resume Candidate 断言

当前只读评估必须满足：

```text
failed Execution
    + worker_owner == None
    + 最新 Checkpoint 存在
    + checkpoint_reason == node.completed
    + checkpoint.execution_status == running
    + checkpoint.node_status == completed
    + 固定原 workflow_version_id
    ↓
eligible Resume Candidate
```

当前不得执行：

- 创建 Resume Execution；
- 抢占 Worker lease；
- 启动 WorkflowRuntime；
- HTTP `/resume`；
- 自动 Resume。

## 10. 禁止验收方式

- 不得通过 Mock Checkpoint Service 作为唯一完成依据；
- 不得通过手工向 `workflow_execution_checkpoints` 插入数据证明 Runtime 已接入；
- 不得修改 `running → running` 状态机；
- 不得让 Gate 自动启动 / 停止 / 重启 API、Scheduler、Worker；
- 不得把 Checkpoint 自动 Resume 能力提前混入本阶段；
- 不得使用服务重启前产生的历史 Execution 作为 Runtime Checkpoint 接入验收的唯一证据；
- 不得通过修改测试断言掩盖 Worker ownership race 或源码基线漂移。

## 11. 当前状态

`0032` migration、Checkpoint 基础服务、Node completion Checkpoint 接入与 Resume Candidate 只读评估已提交到 `main`。开发者必须：

1. 同步最新 `main`；
2. 确认 Source Baseline Gate 通过；
3. 人工重启 API / Worker，使运行进程加载最新代码；
4. 执行 Checkpoint / Resume Candidate targeted、Backend、Real API 与 PostgreSQL persistence Gate；
5. 再决定本 Acceptance 是否标记为最终 Passed。
