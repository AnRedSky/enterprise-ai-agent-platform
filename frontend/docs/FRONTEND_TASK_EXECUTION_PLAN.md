# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。状态必须基于远端 `main`、当前前端代码和本地实际测试结果更新。

## 1. 当前基线

- 远端 `main`：`c0271fc1def0dfb713ebf5f38d75430100b4bf0b`（2026-08-30，Runtime integration event timestamp normalization）。
- 当前前端基线提交：`6577871376b460ac42509e836339d6ccf0135c4d`，基于上述 `main`，完成 Runtime deep link 与 execution context 对齐。
- `frontend` 当前仅比最新 `main` 超前 1 个前端提交，未落后 `main`。
- 本轮文档治理目标：统一 `frontend/docs` 文档职责、索引、状态和提交规则。

## 2. 当前主线：P1.1

**P1.1 深度交互与可观测性工作台** 是当前前端执行指针，重点为：

1. Runtime Tab 化、Execution 按需加载；
2. Runtime 深链恢复 `execution_id` / `workflow_id` / `source` 上下文；
3. Agent 调试上下文读取真实 Agent 与 Published Version；
4. Workflow 生命周期以真实 Workflow / Execution 状态驱动；
5. Retry / Resume / Cancel / Run 仅调用现有生命周期接口；
6. Runtime / Agent / Workflow 诊断上下文保持可追溯。

本轮前端已完成 Runtime deep-link context linkage；其余 P1.1 项目必须继续以源码和 Backend Contract 验证，不以文档代替实现。

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
- FE-P1-04：清理 Element Plus 未解析组件警告。
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

本轮文档治理提交前不宣称前端全量测试通过。此前本地执行 `npx vitest run tests/views/WorkflowLifecycle.test.ts` 曾因项目依赖未正确安装导致 `vitest/config` 与 `@vitejs/plugin-vue` 无法解析，并触发 npx 临时安装提示。该事实说明后续应先恢复项目正式依赖，再使用 `package.json` 正式测试入口，不应使用 npx 临时下载作为验收环境。

下一轮测试必须至少执行：

```powershell
cd frontend
npm install
npm test -- tests/views/WorkflowLifecycle.test.ts
npm test
npm run build
npm run test:gate
```

涉及真实后端时，再执行对应 Real API / Browser E2E。所有结果必须记录实际输出与日期。

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
