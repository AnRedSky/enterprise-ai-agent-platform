# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- 当前阶段：**Phase 1.7 Workflow Trigger Expansion / Scheduling Contract**
- 当前任务：**Phase 1.7-A-01 Scheduled Trigger Backend Contract**
- 当前角色：开发执行
- 测试 Gate 治理：Backend、Frontend、Browser/E2E 三层独立

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5 | **已完成** | Workflow / Governance A～G 全部完成；Circuit Breaker 最终验收通过 |
| Phase 1.6-A | **已完成** | Workflow Trigger Backend Contract；Backend Domain / API / Migration / Contract / Real API 两道 Gate 通过 |
| Phase 1.6-B | **已完成** | Frontend API Type / Vitest / Workflow Trigger Governance UI；Frontend Regression、Trigger Real HTTP、UI 手动验收通过 |
| Phase 1.6-C | **已完成** | Browser / Frontend-Backend E2E 第三独立测试层建立并通过；最终 Browser E2E 1 passed |
| Phase 1.6 | **已正式关闭** | A～C 全部完成，三层 Gate 与实际联调完成 |
| Phase 1.7-A-01 | **开发中** | Scheduled Trigger Backend Contract；先做 Domain / Schema / pytest，暂不实现 Scheduler / Worker |

## 3. Phase 1.6 最终验收

### Backend

```text
Real API Gate
→ 14 passed in 21.28s
→ PASS
```

开发者随后完成 Trigger disabled invoke 的 HTTP 409 边界手工验证，并确认最终联调通过。

### Frontend

```text
Frontend Vitest
→ 50 passed
Frontend production build
→ PASS
Trigger Real HTTP Contract
→ 手动测试全部通过
Frontend UI 手动验收
→ PASS
```

### Browser E2E

```text
Playwright project: Desktop Chrome
Browser E2E Gate
→ 1 passed (3.9s)
→ PASS
```

真实浏览器链路覆盖：

```text
注册隔离用户
→ 创建 Published Workflow fixture
→ Browser 登录
→ Workflow Trigger Governance
→ 创建 manual Trigger
→ Invoke
→ completed Execution
→ Disable
→ UI 禁止 Invoke
→ Enable
→ Delete
```

Phase 1.6-C 最终通过后，Phase 1.6 正式关闭。

## 4. Phase 1.6 工程错误收口

Phase 1.6-C 期间实际发现并修复的工程问题：

1. Playwright Gate 使用 `--project="Desktop Chrome"`，但配置未声明同名 project。
2. E2E fixture 对认证注册状态码的错误断言导致 404 预期与真实 API 不一致；已按真实 HTTP Contract 修正。
3. Workflow Select 的 Element Plus input 被 selected item 拦截；E2E 改为稳定的可见 Select 交互。
4. Published Workflow 文本同时存在于页面与下拉选项，导致 strict mode violation；E2E 选择范围已收窄到可见 dropdown。
5. Delete confirmation 存在多个“确定”按钮；E2E 已将确认定位限定到可见 MessageBox。

相关工程错误记录统一位于 `docs/error-tracking/`。

## 5. Phase 1.7 下一阶段规划基线

Phase 1.6 已验证 manual Trigger 的真实业务入口闭环。下一阶段采用“先 Contract、后 Scheduler”的原则，第一项为 Scheduled Trigger Backend Contract。

Phase 1.7 分解：

```text
1.7-A Scheduled Trigger Backend Contract
      ↓
1.7-B Scheduler execution / persistence integration
      ↓
1.7-C Frontend Schedule Governance UI Contract
      ↓
1.7-D Real HTTP + Browser E2E scheduling contract
```

1.7-A 明确不实现：

- MQ / Worker
- Event Bus
- Cron daemon
- Temporal / Airflow 等 Workflow Engine
- 任意 Cron DSL

首个 Schedule Contract 采用可测试的 `timezone + interval_seconds` 基线；保存 Schedule 不自动创建 Execution。

## 6. 当前立即执行任务

**Phase 1.7-A-01：Scheduled Trigger Backend Contract**

固定顺序：

```text
Backend Domain + Schema
→ pytest / API Contract
→ migration（仅在需要时）
→ Real API
→ Frontend
→ Frontend Gate
→ 联调
→ Browser E2E
→ 文档
→ main
```

本状态文件只在实际结果确认后更新，不预先宣称未执行的 Gate 通过。
