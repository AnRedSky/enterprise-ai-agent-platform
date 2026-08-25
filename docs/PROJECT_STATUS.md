# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发并已有本地 Acceptance 结果；Frontend / Browser E2E 正在完成最终验收汇总。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 已完成 Workflow Trigger Browser E2E 的 API Client、Auth、Workflow Version、正式路由、Browser Session、Element Plus Select、Trigger 持久化实体等待、Scheduler UI 异步初始化同步以及持久化 Config Contract 对齐。

开发者最新本地反馈已经实际通过 Workflow Trigger Browser E2E：真实浏览器完成 Scheduled Trigger 创建、真实 Scheduler API 状态确认、Scheduler UI 状态展示，并完成 PostgreSQL 持久化 Config 四字段最终断言。

本轮不再存在未验证的 Browser Gate 结论；结果以开发者本地实际执行为准。

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：
  - Scheduled Trigger 持久化 Config 断言已与正式 Contract 对齐；
  - 完整验证 `timezone / interval_seconds / misfire_policy / catch_up_limit`；
  - 保留最终 `toEqual`，不降低真实持久化断言强度。
- `docs/04-errors/2026-08-25-browser-e2e-trigger-config-contract.md`：
  - 记录 Trigger 持久化 Config 断言落后于正式 Scheduler Contract 的工程错误、根因、修复边界和本地验收要求。

## 已完成的 Browser / Frontend Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过（79 passed + production build）
Workflow Trigger Browser Gate：本地实际通过（1 passed；脚本最终输出 [PASS]）
```

以上结果均基于开发者本地实际反馈，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build                         ✓ 已通过
Workflow Trigger Browser E2E                              ✓ 已通过
Organization Browser E2E / Model Provider Browser E2E      ↓ 重新确认
Backend default regression                                ↓ 重新确认
Tenant Safe Real API Gate                                 ↓ 重新确认
Scheduler 多实例 lease / misfire / Execution / Audit Trace Acceptance 汇总
                                                            ↓
Phase 2.4 Passed 评估
```

Workflow Trigger Browser Gate 已完成，但 Phase 2.4 仍不得直接标记 Passed。必须完成剩余 Organization / Model Provider Browser E2E、Backend default regression、Tenant Safe Real API Gate，以及 Scheduler Acceptance 汇总后再进行最终评估。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；测试应匹配真实生产 UI 语义并使用稳定 test hooks；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果。
