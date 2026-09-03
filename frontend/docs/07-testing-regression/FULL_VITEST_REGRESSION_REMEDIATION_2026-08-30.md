# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 历史基线

`main` 与 `frontend` 已通过合并提交同步；2026-09-03 的最新 `main` 已包含 Delegation Real API 并发 Fixture 事务边界修复，随后合入 `frontend`。

2026-08-30 的本地基线为 34 个测试文件中 2 个失败、153 个测试中 2 个失败，集中在 Runtime Operations 页面异步渲染与诊断错误可见性。

## 2. 2026-09-03 本地反馈

用户本地 `frontend` 执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

结果：

```text
Test Files  5 failed (5)
Tests       6 failed | 12 passed (18)
```

本轮反馈暴露的失败可以归纳为四类：

1. **Runtime Correlations 静态契约测试与当前实现变量命名不一致**：测试要求 `audit.workflow_execution_id`，当前实现使用 `focusedAudit.workflow_execution_id` 与 `resolvedFact as RuntimeCorrelationAudit`，实际 durable fact 已存在且没有数组位置推断。
2. **Integrations 空状态测试未使用 Element Plus 组件契约查找按钮**：测试在默认投递目标 Tab 中查找“新建事件订阅”，并使用原生 `button` 查询；实际测试环境下 Tab 内容由 Element Plus 组件包装，导致原生查询结果不稳定。
3. **Operations Console 测试依赖渲染时序及 Element Plus 内部 DOM**：Audit 行数据在异步请求完成后才进入页面；Tab inventory 直接读取 `ElTabPane` 的 props 在当前挂载方式下返回空集合。
4. **Organizations 的 `pending` 状态缺少显式中文映射**：测试要求 `pending → 待处理`，当前实现将其视为未知状态。

## 3. 本轮修复

### 3.1 Runtime Correlations / Full-site static audit

收窄 `forbiddenDurableFactPatterns` 的数组位置检查范围，只检查真正可能用于 Durable Relationship 推断的关系集合：`items / versions / destinations / providers / triggers`。

`workflows.value[0]` 和 `executions.value[0]` 属于页面默认选择/聚焦对象，并非从一个 Durable Fact 推导另一个实体关系；将它们纳入该关系审计会产生误报。关系导航仍必须使用显式 durable ID。

### 3.2 Integrations

空状态测试改为通过 `findAllComponents(ElButton)` 查找真实 Element Plus Button，并断言其 `disabled` component prop，而不是依赖原生 DOM `button.disabled`。这样测试验证的是页面的组件契约：没有投递目标时，“新建事件订阅”入口必须保持禁用。

### 3.3 Operations Console

Audit 查询测试在等待 `auditQuery` 调用后继续等待实际 `provider.health.probe` 文本出现，避免只等待 Promise 调用已经发生而数据状态尚未提交的问题。

Tab inventory 测试改为检查页面实际可见文本中的 7 个正式 Tab 标签：`全局运行态势 / 总览 / 告警 / Provider / Metrics / Audit / 死信`，不再依赖 Element Plus `ElTabPane` 内部 props 在测试挂载环境中的表现。

`NO_DURABLE_HEARTBEAT_FACT` 保持作为后端诊断 reason code 展示，测试验证该 durable diagnostic fact，而不是把它伪装成 Worker/Scheduler 已存活状态。

### 3.4 Organizations

组织状态映射调整为用户可见的纯中文：

- `active` → `已启用`
- `suspended` → `已暂停`
- `pending` → `待处理`
- 未知值 → `未知状态（技术值）`

保持后端状态枚举不变，只调整展示层映射。

## 4. 版本同步事实

本轮开始前 `frontend` 已与当时 `main` 同步；随后本轮修复形成独立原子提交。当前 `main` HEAD 为：

`b71e31b1c6e670b69f2f26b9db99f0ee4e2a34c1`

当前 `frontend` HEAD 为：

`79760c4154fda4151690e1ea63e3fd47c4704b9c`

因此当前 `frontend` 包含本轮 3 个代码修复提交，尚未把这些新的前端修复合并回 `main`。下一轮应继续以最新 `main` 为基线进行同步检查，避免产生新的分叉。

## 5. 验证状态

由于当前 ChatGPT 执行环境无法访问用户 Windows 工作树，也无法安装项目依赖或直接执行用户机器上的 `npm test`，本轮没有伪造本地通过结果。

用户提供的是本轮修复前的失败结果：**5 failed files / 6 failed tests / 12 passed / 18 total**。上述修复已经提交到 `frontend`，但必须由用户在同步后的本地工作树重新执行验证。

标准验证顺序：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
npm run test:unit
npm run build
npm run test:gate
```

需要真实浏览器验证时再执行：

```powershell
npm run test:e2e
```

项目已有 `frontend/scripts/test/` 下的自动化脚本负责完整回归；测试不得自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis，测试数据由 Fixture 自动生成。

## 6. 当前状态

**本轮代码修复已完成，待本地验证。**

不能将本轮状态标记为“全量通过”，直到用户本地重新执行 targeted regression、`npm run test:unit`、`npm run build` 和 `npm run test:gate` 并提供实际结果。
