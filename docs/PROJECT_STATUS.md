# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发；Frontend / Browser E2E 已完成本轮实际验证；普通 Tenant Safe Real API Gate 已通过；Scheduler Restart Acceptance 仍需开发者在最新 main 上重新执行确认。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

远端 `main` 已继续推进到历史 Workflow Definition 兼容修复。本轮本地反馈暴露了另一类历史数据问题：Scheduler 对旧版本 `{"nodes": []}` 的 published Workflow 仍使用当前严格 Runtime Definition Contract 校验，导致真实 Backend 启动后周期性输出 422。

本轮已在 main 实现受控兼容：历史已发布空节点 Workflow 仅允许从 Scheduler 执行路径显式开启兼容；新版本发布、普通 Execution 创建和非法非空历史节点仍保持严格 Contract。该修复的本地测试状态尚待开发者重新执行，不预填通过结果。

## 本轮工程变更

- `backend/app/runtime/workflow/runtime.py`
  - `validate_definition()` 增加显式 `allow_legacy_empty_nodes` 边界；默认仍拒绝空 `nodes`。
  - `execute()` 透传历史空节点兼容开关。
- `backend/app/services/workflow/execution.py`
  - `WorkflowExecutionService.run()` 透传历史空节点兼容开关。
  - manual / 普通 Execution 路径默认不启用兼容。
- `backend/app/services/trigger/service.py`
  - scheduled Trigger 仅在已发布 Workflow 路径显式启用历史空节点兼容。
- `backend/tests/unit/test_workflow_definition_legacy_compatibility.py`
  - 新增严格 Contract、显式历史兼容、非法非空节点继续拒绝测试。
- `docs/04-errors/2026-08-25-scheduled-trigger-historical-definition-compatibility.md`
  - 记录 Scheduler 历史 Definition 兼容问题、根因、边界与验证流程。

## 当前 Gate 状态

```text
Backend default regression                         ↓ 需在本轮修复后重新执行
Tenant Safe Real API Gate                         ↓ 需重新执行
Scheduler Restart Acceptance                      ↓ 需重新执行
Backend Regression Gate                            ↓ 需重新执行
Frontend Regression Gate                           ✓ 上轮本地实际通过
Workflow Trigger Browser Gate                     ✓ 上轮本地实际通过
```

上轮开发者反馈：

```text
Backend default regression: 397 passed, 3 skipped, 36 deselected
Tenant Safe Real API Gate: 35 passed
Frontend Regression: 79 passed + production build
Workflow Trigger Browser E2E: 1 passed
```

以上是上一轮实际反馈，不代表本轮兼容修复已经通过。当前不得将本轮修复标记为 Passed，直到开发者重新执行自动化 Gate。

## 当前兼容边界

```text
新 draft/testing -> published
    -> 严格 Runtime Definition Contract
    -> nodes == [] 拒绝

历史 published + nodes == []
    -> Scheduler 显式兼容
    -> 按无操作 Workflow 执行

历史 published + 非空非法 nodes
    -> 仍拒绝
    -> 不猜测历史执行语义
```

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果；
- Scheduler Restart Acceptance 不得让测试自身启动的多个 Scheduler worker 共享同一目标 slot；bootstrap 临时服务完成 fixture 准备后必须退出；
- 历史 Definition 兼容不得扩大为任意非法节点自动转换；只有可确定语义的历史空节点允许受控兼容。
