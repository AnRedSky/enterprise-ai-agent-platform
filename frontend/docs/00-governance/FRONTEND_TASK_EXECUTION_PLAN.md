# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。状态必须基于远端 `main`、当前前端代码和本地实际测试结果更新。

## 1. 当前基线

- 远端 `main`：`fc8a21b28bb88198a1a95538b3c69914a881c824`（2026-08-30，Runtime canonical metric subset acceptance tests）。
- `frontend` 已快进同步到该 `main`，本轮后续实现直接基于此基线，不创建新的功能分支。
- `main` 已包含此前 Workflow 生命周期身份修复：Workflow 页面展示真实 `Workflow.name`，并为单元测试注册 `v-loading` 指令桩。
- 用户本地此前存在 Node 依赖目录不完整的问题：`node_modules` 存在但 `node_modules/.bin/vite.cmd` 不存在；`npm ci` 因 Windows `@esbuild/win32-x64/esbuild.exe` 文件锁返回 EPERM，故本地验证仍需重新安装依赖后执行。

## 2. 当前主线：P1.1 / P1.3 / P1 稳定性

**P1.1 深度交互与可观测性工作台** 当前继续收敛 Runtime / Agent / Workflow 诊断闭环。

### P1.3：Runtime ↔ Workflow 双向深链

状态：**进行中**。

已实现：

1. Workflow 生命周期页面读取真实 `workflow_id` query；
2. query ID 必须先在 `GET /workflows` 返回集合中确认，再加载版本/触发器/Execution；
3. Runtime 在存在真实 `workflow_id` 时显示“返回 Workflow 生命周期”；
4. Runtime → Workflow 仅携带 `workflow_id` 与 `source=runtime`；
5. Workflow → Runtime 继续携带真实 `execution_id` / `workflow_id` / `workflow_version_id`；
6. Vitest 覆盖双向深链及无上下文安全回退。

未完成：本地 targeted/full Vitest、build、test gate、真实 API 与 Browser E2E 尚未执行。

### FE-P1-04：Element Plus 未解析组件/指令警告治理

状态：**进行中**。

本轮已实现：

1. 应用入口 `frontend/src/main.ts` 导入 Element Plus 官方 `vLoading`；
2. 通过 `app.directive("loading", vLoading)` 全局注册；
3. 新增 `frontend/tests/main.test.ts` 验证启动层注册行为；
4. 新增回归文档 `frontend/docs/07-testing-regression/ELEMENT_PLUS_LOADING_DIRECTIVE_REGRESSION.md`。

未完成：本地 targeted/full Vitest、build、test gate 与 Browser E2E 尚未执行。

## 3. 长期任务队列

### P0：核心业务闭环

| ID | 领域 | 目标 | 状态 | 验收 |
|---|---|---|---|---|
| FE-P0-01 | Agent | 创建 → Version → Publish → Runtime → Trace/Audit 闭环 | 进行中 | View + API + Real 联调 |
| FE-P0-02 | Workflow | 编辑 → 校验 → 发布 → Execution → Trace | 进行中 | View + API + E2E |
| FE-P0-03 | Runtime | Execution → Event → Trace → Audit 统一详情链路 | 进行中 | View + API + E2E |
| FE-P0-04 | Knowledge | 知识资产 → 检索 → Agent 关联 → Runtime 验证 | 待实施 | View + API |
| FE-P0-05 | Tool | 工具配置 → Agent 关联 → Runtime 调用结果 | 待实施 | View + API |
| FE-P0-06 | Organization | 组织 → 成员 → 权限 → 资源边界 | 待实施 | View + API + E2E |
| FE-P0-07 | Model Provider | Provider/Model 配置与 Agent 使用关系 | 待实施 | View + API |
| FE-P0-08 | Audit | 跨领域操作证据查询与详情 | 待实施 | View + API |
| FE-P0-09 | Integration | Event → Delivery → Audit → Replay → Dead Letter | 待实施 | View + Real API |

### P1：稳定性与企业级体验

- FE-P1-01：统一 Loading / Empty / Error / Success / Permission 状态。
- FE-P1-02：统一错误分类与用户提示隔离。
- FE-P1-03：统一中文状态映射，未知值安全回退。
- FE-P1-04：清理 Element Plus 未解析组件警告（本轮继续）。
- FE-P1-05：统一 PageHeader / Toolbar / MetricCard / DataTable / DetailPanel 等公共模式。
- FE-P1-06：建立 1440 / 1280 / 1024 / 768 / 390 响应式验收矩阵。
- FE-P1-07：补充核心页面 Playwright 用户旅程。
- FE-P1-08：完成 P1.1 Runtime / Agent / Workflow 深度交互与可观测性工作台。

### P2：2.10-I 后端稳定后再实施

- Provider Registry / Health；
- Alert Rule 与 firing/recovery 生命周期；
- Notification Routing / Provider fallback；
- Notification SLO / Route Metrics；
- Runtime Alert Scheduler 运维视图；
- Prometheus / OpenTelemetry 配置与观测状态。

前置条件：对应 Backend Contract 稳定、Real API 可验收、持久化链路稳定、Runtime Acceptance 明确完成范围。

### P3：平台化长期能力

- Design System 与 Design Token；
- 全局搜索与快捷命令；
- 页面级权限矩阵与通知中心；
- Dashboard 趋势与运营驾驶舱；
- 无障碍与响应式深化；
- 性能预算、资源优化和可观测前端；
- 主题 / 国际化 / 大屏。

## 4. 固定执行流程

```text
同步远端 main
    ↓
确认 Backend Contract / Tests / Acceptance
    ↓
检索现有 API / Types / View / Components / Tests / Docs
    ↓
确定最小业务切片
    ↓
API Types → View / Component → Vitest
    ↓
targeted test → npm test → npm run build → npm run test:gate
    ↓
必要时 Real API / Browser E2E
    ↓
同步 frontend/docs / 项目状态
    ↓
一个原子提交
```

禁止以文档提交替代实现；禁止通过多个中间提交拆散同一交付单元。

## 5. 当前测试事实

用户此前本地 `WorkflowLifecycle.test.ts` 为 3 个测试 2 通过、1 失败；失败原因是旧版本未渲染 `Workflow.name`，并存在 `Failed to resolve directive: loading` 警告。远端代码已修复 Workflow 名称测试，并在本次 FE-P1-04 中补齐生产入口 `v-loading` 注册。

用户最新环境又反馈 `npm run dev` 无法找到 `vite`，随后 `npm ci` 因 Windows `esbuild.exe` 文件锁 EPERM 中断。因此当前不能宣称本地测试通过；必须先解除文件锁、清理 `node_modules` 并执行 `npm ci`。

本地验收至少执行：

```powershell
cd frontend
npm ci
npm test -- tests/main.test.ts tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeWorkspaceTabs.test.ts
npm test
npm run build
npm run test:gate
npm run test:e2e
```

需要真实后端时再执行对应 Real API / Browser E2E。没有实际执行证据，不得把计划或代码检查结果写成“通过”。

## 6. 完成定义

任务只有同时满足以下条件才能标记 `已完成`：

- 后端能力稳定；
- Contract 与 TypeScript 类型一致；
- 用户操作链路完整；
- Loading / Empty / Error / Success / Permission 完整；
- UI 文本和错误边界符合规范；
- 安全与 tenant boundary 正确；
- targeted / full Vitest 实际通过；
- build 与 test gate 实际通过；
- 必要的 Real API / E2E 实际完成；
- `frontend/docs` 已同步；
- 原子提交完成。

## 7. 状态规则

只允许：`待实施`、`进行中`、`阻塞`、`已完成`。

状态变化必须有对应代码、测试或验收事实。没有实际执行证据，不得把“计划”“预期”写成“通过”。
