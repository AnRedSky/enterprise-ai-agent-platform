# 前端长期优化路线图

## 当前执行原则

前端不追赶尚未稳定的后端功能。以远端 `main` 为基线，按后端 Contract、测试和真实验收成熟度决定前端开发顺序。当前 2.10-A～H 已完成，2.10-I 仍在开发中；因此当前前端主线优先补齐已有稳定业务闭环。

## 执行优先级

| 优先级 | 领域 | 前端目标 | 前置条件 |
|---|---|---|---|
| P0 | Agent | 创建、版本、发布、运行调试、运行标识关联 | 已稳定 Agent Contract |
| P0 | Workflow | 编排、校验、发布、执行、Trace | 已稳定 Workflow/Runtime Contract |
| P0 | Runtime | Execution、Event、Trace、Audit 完整链路 | Runtime Integration 已验收 |
| P0 | Knowledge | 知识资产、检索、Agent 关联 | Knowledge API 稳定 |
| P0 | Tool | 工具配置、关联、调用结果 | Tool API 稳定 |
| P1 | Organization | 成员、角色、权限和 tenant 边界 | IAM/Organization Contract 稳定 |
| P1 | Model Provider | Provider、Model 配置及 Agent 使用关系 | Provider Contract 稳定 |
| P1 | Audit | 跨领域治理证据链 | Audit Contract 稳定 |
| P1 | Integration | Event、Delivery、Replay、Dead Letter、Audit | 2.10-A～H 稳定能力 |
| P2 | 2.10-I | Provider Health、Alert、Notification、Metrics、Export | 对应后端 Runtime Acceptance 完成 |
| P3 | 企业体验 | Design System、E2E、性能、无障碍、搜索、通知中心 | 核心业务闭环稳定 |

## 阶段目标

### 阶段 A：核心业务闭环

完成 Agent → Workflow → Runtime 的前端连续旅程。重点不是视觉重做，而是保证用户可以从资产配置进入真实执行，并获得可追踪的 Execution / Trace / Audit 信息。

### 阶段 B：能力依赖完善

完成 Knowledge / Tool 与 Agent、Runtime 的关联；保证知识检索和工具调用结果能够在运行记录中解释。

### 阶段 C：企业治理

完成 Organization / Model Provider / Audit / Integration 的稳定功能闭环，并建立 tenant、权限、审计和可靠投递的统一页面语言。

### 阶段 D：新后端能力前端化

待 2.10-I Runtime Acceptance 完成后，再实施 Provider Registry / Health、Alert、Notification Routing、Provider fallback、SLO、Route Metrics、Export 等页面能力。前端不得以 Mock 或猜测 Contract 提前标记完成。

### 阶段 E：生产级体验

在核心功能稳定后，统一 Design Token、公共组件、响应式、无障碍、性能预算和 Playwright 关键用户旅程。

## 每个迭代周期

```text
1. 同步远端 main
2. 核对后端 Contract / Tests / Acceptance
3. 选取一个最小业务切片
4. API Types
5. UI / Component
6. Vitest
7. targeted test
8. 全量 npm test
9. npm run build
10. npm run test:gate
11. 必要时 Real API / E2E
12. 更新 frontend/docs
13. 一个原子提交
```

## 质量目标

- 用户可见文本统一通俗中文；技术标识在诊断场景保留。
- 不直接展示 `error.message`、HTTP 原文或异常堆栈。
- 每个页面具备 Loading / Empty / Error / Success / Permission 状态。
- API 类型、页面行为和测试与 Backend Contract 可追溯。
- 核心业务页面逐步达到桌面端 1440 / 1280 / 1024、平板 768、移动端 390 的响应式验收。
- 核心用户旅程具备真实前后端 E2E 证据。

## 任务状态规则

任务状态只允许使用：`待实施`、`进行中`、`阻塞`、`已完成`。状态变更必须基于实际代码与测试事实，并同步更新任务执行台账和必要 Phase/Acceptance 文档。
