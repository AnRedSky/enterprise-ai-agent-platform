# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`，当前两者已基于同一基线提交，`frontend` 仅保留本轮前端修复提交。

- `main`: `1c46ded7d153567b053c8acae39a608a0a90f342`
- `frontend`: `d8da35d98e1b1e0f3e51272b9be28b42f006b7f1`
- `frontend` 相对 `main`: `ahead_by=1`、`behind_by=0`

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地 targeted regression 反馈

用户在 Windows `frontend` 工作树执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

反馈结果：

```text
Test Files  1 failed | 4 passed (5)
Tests       1 failed | 22 passed (23)
```

唯一失败文件为 `FullSiteConsistencyStaticAudit.test.ts`，最新暴露的问题为：

- `src/views/login/components/LoginForm.vue` 仍使用原始 `<el-card>`。

其余四个 targeted test file 均通过。

## 3. 根因分析

`FullSiteConsistencyStaticAudit.test.ts` 将所有 `src/views/**/*.vue` 的原始 Element Plus Card、Empty、Result 以及 `v-loading` 视为禁止的页面层实现，要求统一通过共享 UI primitive 表达页面结构和状态。

`LoginForm.vue` 是历史遗留的认证入口页面，仍直接使用 `el-card`，且没有采用项目统一的 SurfaceCard 容器和设计 Token。这属于公共 UI primitive 治理遗漏，不属于后端认证 Contract 问题。

## 4. 本轮代码修复

### 4.1 Knowledge Workbench

提交：

- `3f8a13987fb6ef391885c51f52aad7a6d8fd4ee6` — `fix: migrate knowledge workbench to shared state primitives`

调整：

- 移除 Knowledge Workbench 页面中的 `v-loading`；
- 文档、版本、分块空状态统一改为 `StatePanel state="empty"`；
- 检索加载、无结果和初始等待状态统一使用 `StatePanel`；
- 保留 `SurfaceCard` 作为业务区块容器；
- 保留知识库、文档、版本、分块、检索的既有 API 调用和数据结构。

### 4.2 LoginForm

提交：

- `d8da35d98e1b1e0f3e51272b9be28b42f006b7f1` — `fix: migrate login form to shared surface primitive`

调整：

- 原始 `<el-card>` → `SurfaceCard`；
- 登录 API、路由跳转、表单校验和用户可见错误文案保持不变；
- 登录容器改用 `var(--ui-bg-app)` 等共享设计 Token；
- 保持 `width: min(420px, 100%)` 与页面 padding，改善窄屏响应式表现；
- 新增 `LoginForm.test.ts`，覆盖共享容器、认证 API 边界和响应式设计契约。

该修复提交同时包含源码与回归测试，保持单一修复目的。

## 5. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 6. 当前验证状态

当前环境不能直接执行用户 Windows 工作树中的 `npm test`，因此不记录未经实际执行的“通过”。GitHub 源码与提交结构检查已确认：

- `frontend` 相对 `main`：`ahead_by=1`、`behind_by=0`；
- LoginForm 已不再包含 `<el-card>`；
- LoginForm 已使用 `SurfaceCard`；
- LoginForm 回归测试已随同修复提交加入；
- Knowledge Workbench 的 `v-loading` / `el-empty` 已在此前修复中移除。

用户本地先同步：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

然后重新执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts tests/views/LoginForm.test.ts
```

若 targeted regression 全部通过，再执行：

```powershell
npm test
npm run build
npm run test:gate
npm run test:e2e
```

没有实际执行的测试不得记录为通过；测试数据必须由 Fixture / Script 自动生成，不得要求手工填写业务信息，也不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 7. 本地手动验证流程

1. 登录页：确认用户名/密码为空时给出中文校验提示。
2. 登录页：输入有效凭据后确认调用正式 `login` API 并跳转 `/dashboard`。
3. 登录页：认证失败时只显示用户可理解的中文错误，不直接暴露异常正文。
4. 登录页：窄屏宽度下确认 SurfaceCard 不发生水平溢出。
5. Full-site consistency：确认所有 View 不再出现被禁止的历史 presentation primitive。
6. Runtime / Workflow 深链：确认关系仅来自显式 durable ID，不通过数组位置或页面顺序推断。

## 8. 下一步

当前状态保持 **进行中**：本轮 LoginForm 修复、回归测试和 main 同步已完成，但用户 Windows 工作树尚未重新执行包含最新提交的 targeted regression；全量 `npm test`、build、gate、E2E 也尚未由本轮环境实际执行。

下一轮继续遵循：

> **本地实际失败 → 根因分析 → 单一修复 → targeted test → 文档 → 原子提交**

若新的静态审计暴露其他历史 View primitive，再逐个收敛，不进行无关的大规模重构。
