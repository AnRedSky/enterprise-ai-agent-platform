# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 已进入 Backend 模块化整改实施阶段。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first + Persistence 第一版已完成，Runtime persistence / lease / slot 已接入；当前等待 Runtime Gate 本地验证。**

## 本轮执行基线

本轮以远端 `main` 最新提交 `3d0c488` 为基线继续推进。开发准则要求远端 `main` 是唯一开发基线、所有变更直接提交 `main`，并要求模块职责唯一、禁止兼容垫片与重复 Provider、每个新增/重构 Python 模块补充中文职责说明。

此前开发者本地已经实际验证：

```text
378 passed, 2 skipped, 35 deselected
Backend Module Refactor Gate completed
Scheduler Persistence Gate completed
```

其中 Scheduler Persistence Gate 已实际完成 Migration、13 个 Contract tests、2 个真实 PostgreSQL Repository integration tests 与 Backend Regression。

## 本轮新增修复事实

1. `backend/app/services/workflow_scheduler/runtime.py` 已从进程内 interval recovery 改为使用真实 PostgreSQL `WorkflowSchedule` 作为持久化调度状态来源。
2. Runtime 为每个实例生成独立 scheduler owner，通过 `WorkflowSchedulerRepository.claim_due_lease` 进行原子 ownership claim。
3. Runtime 使用持久化 `next_run_at` 生成稳定 `WorkflowScheduleSlot.schedule_slot_key`，slot 唯一键继续作为最终幂等边界。
4. WorkflowExecution 仍统一复用既有 `WorkflowTriggerService.invoke_scheduled`，没有复制第二套 Workflow 执行实现。
5. Runtime 在 Execution 创建后绑定 slot，并通过 lease owner 原子推进 `next_run_at / last_run_at / last_execution_id` 后释放 lease。
6. 首版继续明确 `misfire=skip`：历史积压不逐槽补发，下一次运行从未来时间重新计算。
7. `backend/tests/unit/test_workflow_scheduler_runtime.py` 新增 Runtime 纯计算 targeted tests。
8. `backend/scripts/test/integration/02_scheduler_runtime_gate.ps1` 新增 Runtime Gate，固定执行 Runtime targeted tests + Scheduler Persistence Gate。
9. `docs/04-errors/ERR-0025-durable-scheduler-runtime-persistence.md` 已记录本轮 Runtime 从旧内存槽位切换到持久化 Scheduler 状态的工程问题与验证边界。
10. 新增/重构代码均补充中文职责、边界和关键外部依赖说明。

**以上为代码/文档修复事实，不代表本轮 Runtime 修改已经由开发者本地验证通过。**

## 当前待执行本地验证

先确保依赖与当前仓库一致：

```powershell
cd backend
uv sync --dev
```

然后执行：

```powershell
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q tests/unit/test_workflow_scheduler_runtime.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\02_scheduler_runtime_gate.ps1
```

如 Runtime Gate 失败，必须依据真实失败栈继续修复；不得用 JSON/JSONL 替代 PostgreSQL Scheduler Persistence，也不得通过兼容垫片恢复旧 Runtime 路径。

## Backend 模块化整改纪律

```text
远端 main 唯一基线
→ 领域职责唯一
→ 生产/测试/评估/验证 import 全量切换
→ 删除旧文件
→ 全仓旧路径搜索 = 0
→ 重复实现检查 = 0
→ 中文模块职责说明
→ targeted tests
→ Backend Regression
```

Provider 正式技术适配统一位于 `app/infrastructure/providers/`；数据库 Engine / Session 正式实现统一位于 `app/infrastructure/db/`。Backend 模块化目录、职责与迁移规则继续遵循架构文档和迁移映射表。

## Phase 2.4 下一执行任务

1. 开发者本地执行 Scheduler Runtime Gate，确认 Runtime persistence / lease / slot 接入没有引入回归；
2. 补充 Runtime tenant isolation / misfire targeted integration；
3. 完成 Scheduler API Contract 与持久化状态可观测性；
4. 完成 Tenant Safe Real API Gate；
5. 完成 Audit / Trace 与 Scheduler lifecycle 完整验收；
6. 所有 Gate 实际通过后，再推进前端/API 联调。
