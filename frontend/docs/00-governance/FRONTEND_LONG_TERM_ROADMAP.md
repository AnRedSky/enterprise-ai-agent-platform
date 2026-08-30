# 前端长期优化路线图

## 1. 总体原则

前端以远端 `main` 的稳定 Backend Contract 为事实基线，不追赶尚未完成 Runtime Acceptance 的后端能力。优化目标从“页面可用”逐步提升到“业务闭环、可观测、可诊断、可治理、可持续演进”。

## 2. 当前阶段：P1.1

当前重点是 **Runtime 可观测性工作台 + Agent 对话调试 + Workflow 生命周期 UI 的深度交互**。

### P1.1 目标

- Runtime：Tab 化、按需加载、Execution 深链、事件/Trace/Audit/Workflow 上下文联动；
- Agent：真实 Agent + Published Version 调试上下文，模型、版本、System Prompt 和 Runtime 入口可追溯；
- Workflow：真实 Workflow / WorkflowExecution 生命周期展示，Run / Cancel / Retry / Resume 与 Runtime Execution 形成连续旅程；
- 全部上下文使用真实资源 ID，不复制后端状态机。

## 3. 阶段路线

| 阶段 | 目标 | 主要内容 | 进入条件 |
|---|---|---|---|
| P0 | 核心业务闭环 | Agent → Workflow → Runtime → Trace/Audit | Backend 核心 Contract 稳定 |
| P1 | 企业级体验 | 状态完整性、错误边界、统一 UI、响应式、E2E | 核心闭环可用 |
| P1.1 | 深度可观测交互 | Runtime Tab、按需加载、Agent Debug、Workflow Execution 联动 | 当前执行阶段 |
| P2 | 2.10-I 前端化 | Provider、Health、Alert、Notification、Metrics、Export | Backend Runtime Acceptance 完成 |
| P3 | 平台化 | Design System、搜索、通知中心、权限矩阵、无障碍、性能 | 核心领域稳定 |
| P4 | 运营智能化 | 趋势分析、异常关联、跨资源诊断、运营驾驶舱 | P2/P3 稳定 |

## 4. P1.1 后续拆解

### P1.1-A Runtime 工作台

1. 完成健康概览与 Execution Tab 的清晰边界；
2. Execution 列表分页、筛选、刷新与深链；
3. Execution 详情按需加载 Event / Trace / Audit / Workflow；
4. 状态变化只以 Backend Contract 为准；
5. 诊断上下文可以从 Runtime 反向进入 Agent / Workflow。

### P1.1-B Agent 调试

1. Agent 列表与 Published Version 统一上下文；
2. 对话调试显示版本、模型和必要运行元数据；
3. 调试请求产生的 Runtime Execution 可直接追踪；
4. 从 Execution 返回 Agent 时保持上下文；
5. 失败场景提供可恢复操作和诊断信息，但不泄漏原始异常。

### P1.1-C Workflow 生命周期

1. Workflow 状态与最近 Execution 同屏；
2. Pending / Running / Completed / Failed / Cancelled 等状态统一映射；
3. Run / Cancel / Retry / Resume 调用正式 API；
4. 操作完成后刷新真实 Execution 状态；
5. Execution → Runtime → Trace / Audit 保持可追溯。

## 5. P2：2.10-I 后端稳定后的前端化

不得提前通过 Mock 标记完成。后端 Acceptance 稳定后按以下顺序：

```text
Provider Registry / Health
        ↓
Alert Rule / Firing / Recovery
        ↓
Notification Routing / Provider fallback
        ↓
Delivery / Idempotency / Failure Audit
        ↓
SLO / Route Metrics
        ↓
Scheduler Operations
        ↓
Prometheus / OpenTelemetry / Export
```

## 6. P3：企业级平台能力

- Design Token + 公共组件版本治理；
- 页面级权限与 tenant-aware UI；
- 全局搜索、命令面板、通知中心；
- Playwright 核心用户旅程；
- 1440 / 1280 / 1024 / 768 / 390 响应式矩阵；
- 键盘操作、语义结构、对比度等无障碍验收；
- 首屏、路由切换、列表渲染、Bundle 等性能预算。

## 7. P4：运营与诊断智能化

长期目标不是增加图表数量，而是减少定位问题的路径：

```text
异常
 ↓
资源
 ↓
Execution
 ↓
Event / Trace
 ↓
Agent / Workflow / Provider
 ↓
Audit / Delivery
 ↓
可执行恢复动作
```

最终形成跨 Agent、Workflow、Runtime、Integration 的统一诊断工作台。

## 8. 每轮交付质量门槛

每轮必须遵循：

1. 同步远端 `main`；
2. 核对 Backend Contract / Tests / Acceptance；
3. 检索已有实现和文档，避免重复能力；
4. 实现最小业务切片；
5. targeted Vitest；
6. 全量 `npm test`；
7. `npm run build`；
8. `npm run test:gate`；
9. 必要时 Real API / Browser E2E；
10. 更新 `frontend/docs`；
11. 一个语义单一的原子提交。

## 9. 长期质量指标

- Contract 漂移：0；
- 未处理页面状态：0；
- 用户可见原始后端错误：0；
- 新增重复 API / 状态机 / Provider：0；
- 核心旅程真实 E2E 覆盖率持续提升；
- 关键页面响应式验收覆盖 1440 / 1280 / 1024 / 768 / 390；
- 高风险操作均具备权限与确认保护；
- 关键诊断链路可从资源追踪到 Execution / Trace / Audit。
