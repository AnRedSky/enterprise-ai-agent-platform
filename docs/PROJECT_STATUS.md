# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发；Frontend / Browser E2E 已完成本轮实际验证；当前 Backend Regression 的 Tenant Safe Real API Gate 因 Scheduler restart 生命周期与普通 Real API Gate 混跑导致的非确定性已完成工程修复，等待本地重新验收。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 基线为 `f26f5a5`，Workflow Trigger Browser E2E、Organization Browser E2E、Model Provider Browser E2E 以及 Frontend Regression 均已有开发者本地实际通过结果。

本轮最新反馈进一步暴露 Backend Gate 的生命周期隔离问题：普通 Tenant Safe Real API Gate 同时执行 Scheduler 真实进程 restart acceptance，而开发环境可能已经存在另一个 API/Scheduler 进程。两个 Scheduler 共享 PostgreSQL 后会竞争同一 Scheduled Trigger 的 lease / slot，使 restart acceptance 出现一次失败、随后独立重跑又通过的非确定性结果。

## 本轮工程变更

- `backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1`：
  - 普通 Real API Gate 排除 `test_scheduler_restart_api.py`；
  - Scheduler 真实服务停止/重启验收保持独立，不再与普通 HTTP API Gate 混跑；
  - Gate 输出明确区分普通 Real API 与独立 lifecycle acceptance。
- `backend/scripts/test/api-real/02_run_scheduler_restart_acceptance.ps1`：
  - 增加 `127.0.0.1:8000` 独占端口检查；
  - 已有 API/Scheduler 进程运行时立即失败并给出明确操作要求，避免第二个 Scheduler 与现有 worker 竞争 PostgreSQL slot。
- `docs/04-errors/2026-08-25-real-api-gate-scheduler-restart-isolation.md`：
  - 记录本轮真实失败、非确定性根因、修复边界与验收流程。

## 已完成的 Browser / Frontend Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过（79 passed + production build）
Workflow Trigger Browser Gate：本地实际通过（1 passed；脚本最终输出 [PASS]）
```

以上结果均基于开发者本地实际反馈，不预填通过结果。

## Backend 当前 Gate 状态

```text
Backend default regression                         ✓ 397 passed / 3 skipped / 36 deselected
Tenant Safe Real API Gate（旧编排）               ⚠ 首次 1 failure，随后独立重跑 36 passed
Scheduler Restart Acceptance                      ⚠ 需要在独占 Scheduler 条件下重新执行
Backend Regression Gate                            ↓ 等待上述修复后的本地 Gate 重新确认
```

本轮不把“随后独立重跑通过”直接当作最终 Closure；必须按修复后的脚本重新执行并记录实际结果。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；测试应匹配真实生产 UI 语义并使用稳定 test hooks；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果；
- Scheduler Restart Acceptance 不得与另一个运行中的 Scheduler 进程共享同一测试数据库执行。
