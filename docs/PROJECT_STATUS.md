# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发；Frontend / Browser E2E 已完成本轮实际验证；普通 Tenant Safe Real API Gate 已通过，Scheduler Restart Acceptance 尚待本地重新执行确认。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 基线为 `b135876`，Workflow Trigger Browser E2E、Organization Browser E2E、Model Provider Browser E2E、Frontend Regression、Backend Regression 以及 Tenant Safe Real API Gate 均已有开发者本地实际通过结果。

本轮最新反馈表明 Scheduler Restart Acceptance 尚未开始执行：旧脚本要求 `127.0.0.1:8000` 独占，而开发环境已有 API/Scheduler 占用该端口，因此 Gate 在真正启动测试前即失败。该问题属于测试编排的环境耦合，不是 Scheduler Runtime Contract 失败。

## 本轮工程变更

- `backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1`：
  - 普通 Real API Gate 排除 `test_scheduler_restart_api.py`；
  - Scheduler 真实服务停止/重启验收保持独立，不再与普通 HTTP API Gate 混跑；
  - Gate 输出明确区分普通 Real API 与独立 lifecycle acceptance。
- `backend/scripts/test/api-real/02_run_scheduler_restart_acceptance.ps1`：
  - 不再固定要求 `127.0.0.1:8000` 空闲；
  - 启动前自动申请本机空闲临时端口作为 fixture bootstrap API；
  - bootstrap 完成后释放临时进程，真正的 restart acceptance 继续由测试自身动态申请独立端口；
  - finally 中清理 `API_BASE_URL`、Token、Trigger fixture 等测试环境变量。
- `docs/04-errors/2026-08-25-real-api-gate-scheduler-restart-isolation.md`：
  - 记录旧版固定端口导致 Gate 在开发环境已有 API 服务时无法启动的问题；
  - 明确本次修复只解除无必要的端口耦合，不放宽 Scheduler restart 的真实进程生命周期边界。

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
Tenant Safe Real API Gate（修复后）               ✓ 35 passed
Scheduler Restart Acceptance                      ↓ 待执行
Backend Regression Gate                            ✓ Backend regression + migration + tenant-safe API 均通过；Phase 2.4 Closure 等待 restart acceptance
```

`Scheduler Restart Acceptance` 必须在本次端口自动化修复后重新执行；在实际结果返回前，不提前记录 Phase 2.4 Passed。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；测试应匹配真实生产 UI 语义并使用稳定 test hooks；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果；
- Scheduler Restart Acceptance 不得让测试自身启动的多个 Scheduler worker 共享同一目标 slot；bootstrap 临时服务完成 fixture 准备后必须退出。
