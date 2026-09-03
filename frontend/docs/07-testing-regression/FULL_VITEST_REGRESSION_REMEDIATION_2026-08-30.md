# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`，当前两者已基于同一基线提交，`frontend` 仅保留本轮前端修复提交。

- `main`: `1c46ded7d153567b053c8acae39a608a0a90f342`
- 本轮修复前 `frontend`: `4f2e6a60b4024cd8f908567a1b75bd834ba96998`
- 本轮修复后 `frontend`: 待提交

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地 targeted regression 反馈

用户在 Windows `frontend` 工作树执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts tests/views/LoginForm.test.ts
```

反馈结果：

```text
Test Files  1 failed | 5 passed (6)
Tests       1 failed | 25 passed (26)
```

唯一失败文件为 `FullSiteConsistencyStaticAudit.test.ts`，最新暴露的问题为：

- `src/views/organizations/detail.vue` 仍使用 `v-loading="membersLoading"`。

其余五个 targeted test file 均通过。

## 3. 根因分析

`FullSiteConsistencyStaticAudit.test.ts` 将所有 `src/views/**/*.vue` 的原始 Element Plus Card、Empty、Result 以及 `v-loading` 视为禁止的页面层实现，要求统一通过共享 UI primitive 表达页面结构和状态。

`organizations/detail.vue` 已经使用 `SurfaceCard` / `StatePanel` 处理页面级和成员错误/空状态，但成员表格仍保留历史 `v-loading` 指令。这是公共状态展示治理未完成，不属于组织 API Contract 或权限业务逻辑问题。

## 4. 本轮代码修复

### 4.1 Organization detail

本轮修复：

- 移除成员表格上的 `v-loading`；
- 成员请求期间使用 `StatePanel state="loading"` 提供稳定的页面状态反馈；
- 成功后再渲染成员表格；
- 保留成员分页、错误恢复、空状态和真实 membership ID 操作；
- 保留组织/成员 API 调用、权限判断和后端状态刷新语义，不新增业务规则。

### 4.2 回归测试

新增 `OrganizationsDetail.test.ts`，验证：

- 成员 Loading 使用共享 `StatePanel`；
- 页面不再包含 `v-loading` / `el-empty` / `el-result`；
- 成员刷新仍通过既有 `loadMembers` / `reloadMembers` API 边界完成。

代码与测试保持在同一个原子修复提交中。

## 5. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 6. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test`，因此不记录未经实际执行的“通过”。GitHub 源码检查已确认本轮修改目标为 `organizations/detail.vue` 的唯一静态审计失败项，并增加针对该页面的回归测试。

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
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts tests/views/LoginForm.test.ts tests/views/OrganizationsDetail.test.ts
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

1. 进入组织详情页，确认首次加载显示组织详情 Loading。
2. 确认成员列表请求期间显示“正在加载成员”，不出现遮罩错位或水平溢出。
3. 成员加载成功后确认表格正常展示，分页仍可用。
4. 成员加载失败时确认错误状态提供“重试”，且不会暴露原始异常正文。
5. 成员为空时确认显示空状态和“添加成员”动作。
6. 添加、编辑、暂停/恢复、移除、转移所有权仍以真实 membership ID 调用后端并刷新结果。

## 8. 下一步

当前状态保持 **进行中**：本轮针对组织详情 `v-loading` 的代码与回归测试已完成，但用户 Windows 工作树尚未重新执行包含最新提交的 targeted regression；全量 `npm test`、build、gate、E2E 也尚未由本轮环境实际执行。

下一轮继续遵循：

> **本地实际失败 → 根因分析 → 单一修复 → targeted test → 文档 → 原子提交**

若新的静态审计暴露其他历史 View primitive，再逐个收敛，不进行无关的大规模重构。
