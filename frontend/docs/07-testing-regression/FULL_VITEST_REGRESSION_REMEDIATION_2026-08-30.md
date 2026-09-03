# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 历史基线

`main` 与 `frontend` 在本轮修复开始前已同步；2026-09-03 的 `main` HEAD 为 `001e2bd6ab2e4c4d4d5fe7a9f8d05e3b99ee9e0b`。

2026-08-30 的本地基线为 34 个测试文件中 2 个失败、153 个测试中 2 个失败，集中在 Runtime Operations 页面异步渲染与诊断错误可见性。

## 2. 2026-09-03 本地反馈

用户本地 `frontend` 执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

结果：

```text
Test Files  4 failed | 1 passed (5)
Tests       4 failed | 14 passed (18)
```

失败集中为三类：

1. **Full-site static audit**：`DeliveryConsole.vue` 仍存在原始 `el-empty`，违反页面统一状态组件约束。
2. **Integrations 空状态测试**：测试切换到 `subscriptions` 后立即查找 Element Plus Button；Tab 内容存在异步挂载时序，导致组件尚未进入测试树。
3. **Operations Console Tab inventory**：测试依赖 Element Plus Tab 内部运行时 DOM 文本；当前挂载方式下 Tab label slot 不保证出现在 `wrapper.text()` 中。

`Organizations` 与 `IntegrationsUI03UI05` 在用户反馈中已经通过，不再重复实现或修改。

## 3. 本轮修复

### 3.1 DeliveryConsole 统一 Empty State

`frontend/src/views/integrations/DeliveryConsole.vue` 将审计记录为空时的原始 `<el-empty>` 替换为共享 `StatePanel`：

- 保持 `loading / empty / error / permission / success` 状态组件体系一致；
- 不改变投递审计数据或交互行为；
- 避免 Full-site static audit 对页面原始 Element Plus 状态组件的误报。

原子提交：`638bcaffc409d9bb9f58e8209c349f9a6efaa87a` (`fix: align delivery empty state with shared primitive`)。

### 3.2 Integrations Tab 异步挂载契约

`frontend/tests/views/Integrations.test.ts` 保留 Element Plus `ElButton` component contract，同时使用 `vi.waitFor()` 等待“新建事件订阅”按钮真正进入测试组件树，再验证 `disabled` prop。

这样测试关注真实用户契约，而不是 Element Plus Tab 内容同步渲染的内部时序。

原子提交：`a8e43fdc9bd514660d5ee70e42c7b6cb2adeb32c` (`test: stabilize integrations tab assertion`)。

### 3.3 Operations Console Tab inventory 契约

`frontend/tests/views/OperationsConsole.test.ts` 不再依赖 Element Plus Tab runtime DOM 文本。测试直接读取当前 `OperationsConsole.vue` 的正式 Tab label 声明，并验证完整的 7 项导航契约：

`全局运行态势 / 总览 / 告警 / Provider / Metrics / Audit / 死信`

该测试仍验证产品页面的正式文案，但不绑定第三方组件内部渲染结构。

原子提交：`867717eacbd35edbd963644096d3b9e6f78ed639` (`test: stabilize operations tab inventory contract`)。

## 4. Durable Relationship / UI Governance

`FullSiteConsistencyStaticAudit.test.ts` 继续禁止：

- `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- `items / rows / list / executions / traces / audits` 通过 `sort()` / `reverse()` 推导关系；
- 页面直接使用原始 `el-card / el-empty / el-result`；
- View 层 optimistic durable status mutation。

允许的默认选择场景必须与 Durable Relationship 推断明确区分，例如 Workflow/Execution 页面默认聚焦对象不能被关系审计规则误判为实体关联。

## 5. 版本同步事实

修复开始前通过 GitHub compare 确认：

- `main` HEAD：`001e2bd6ab2e4c4d4d5fe7a9f8d05e3b99ee9e0b`
- `frontend` HEAD：`001e2bd6ab2e4c4d4d5fe7a9f8d05e3b99ee9e0b`
- `ahead_by = 0`
- `behind_by = 0`

因此无需额外产生 `main → frontend` 合并提交。本轮随后形成 3 个独立原子提交，当前 `frontend` HEAD 为 `867717eacbd35edbd963644096d3b9e6f78ed639`；这些提交尚未合并回 `main`，符合前端开发分支隔离原则。

## 6. 验证状态

当前执行环境无法访问用户 Windows 工作树，因此没有伪造 `npm test`、`npm run test:unit`、`npm run build` 或 E2E 的本地通过结果；GitHub Actions 对最新修复提交也未返回 workflow run。

用户本地应在更新到最新 `frontend` 后执行：

```powershell
cd frontend
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
npm run test:unit
npm run build
npm run test:gate
```

浏览器 E2E 在基础回归通过后执行：

```powershell
npm run test:e2e
```

测试环境要求保持不变：不得由测试自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis；测试数据必须由 Fixture / 脚本自动生成，禁止人工填写测试信息。

## 7. 本地手动验证流程

1. `git fetch origin` 后确认 `frontend` 已包含最新提交。
2. 安装前端依赖并确认 Node/npm 版本符合项目要求。
3. 启动已有开发环境，不由测试脚本自动拉起后端服务。
4. 进入“集成中心”：
   - 无投递目标时，“新建事件订阅”保持禁用；
   - 页面明确显示“请先创建至少一个投递目标”；
   - 创建投递目标后订阅入口恢复可用。
5. 进入“运维窗口”：确认 7 个正式 Tab 均可见且可切换，Audit 查询结果、Provider、Metrics、死信等内容与后端事实一致。
6. 进入投递管理并打开一条投递记录的审计弹窗：确认无审计记录时使用统一 Empty State，不出现原始 Element Plus Empty 组件。
7. 检查桌面与窄屏布局，确认工具栏、表格、状态面板不发生横向溢出。

## 8. 当前状态

**代码修复已完成，待用户本地重新验证。**

不能将本轮标记为“全量通过”，直到用户本地提供 targeted regression、unit、build、gate 的实际结果。
