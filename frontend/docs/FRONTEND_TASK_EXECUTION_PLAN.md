# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。任务状态必须基于远端 `main` 与本地实际测试结果更新。

## 1. 执行原则

1. **后端稳定能力优先**：只有 Backend Contract、核心业务逻辑、持久化和必要验收稳定后，才进入前端正式实现。
2. **不提前实现未稳定能力**：2.10-I 中尚未完成 Runtime Acceptance 的 Notification → Webhook Worker、通知幂等/去重/失败审计等能力暂不作为前端正式功能基线。
3. **现有 UI 渐进增强**：不复制另一套中文版 UI，不因文本规范而重构现有页面结构；优先补齐真实业务能力。
4. **单一事实来源**：前端 API 类型必须与后端 Contract 对齐，不复制后端业务规则。
5. **一个功能一个原子提交**：源码、测试、必要设计记录属于同一交付单元时一次提交完成。
6. **测试先于完成标记**：未执行的测试不得标记为通过；GitHub Actions 不作为本地开发验收依据。

## 2. 后端能力基线

截至 2026-08-29，远端 `main` 最新提交为 `aed90abd391d19155fb9a25f043f67691a3f9b37`。项目状态显示 Phase 2.10-I 仍在开发中；2.10-A～H 已完成，2.10-I 已具备 Provider Registry、Health、Metric Sampling、Alert Lifecycle、Scheduler 和 Notification Routing 编排切片，但 Notification → Webhook Delivery Worker 真实闭环、通知幂等/去重/失败审计、Prometheus/OTel 治理和最终 Runtime Acceptance 尚未完成。

因此当前前端优先级必须以已稳定的 2.9 与 2.10-A～H 能力为主。

## 3. 长期任务队列

### P0：核心业务闭环

| ID | 领域 | 目标 | 状态 | 验收 |
|---|---|---|---|---|
| FE-P0-01 | Agent | 创建 → Version → Publish → Runtime → Trace/Audit 闭环 | 进行中 | View + API + Real 联调 |
| FE-P0-02 | Workflow | 编辑 → 校验 → 发布 → Execution → Trace | 待实施 | View + API + E2E |
| FE-P0-03 | Runtime | Execution → Event → Trace → Audit 统一详情链路 | 待实施 | View + API + E2E |
| FE-P0-04 | Knowledge | 知识资产 → 检索 → Agent 关联 → Runtime 验证 | 待实施 | View + API |
| FE-P0-05 | Tool | 工具配置 → Agent 关联 → Runtime 调用结果 | 待实施 | View + API |
| FE-P0-06 | Organization | 组织 → 成员 → 权限 → 资源边界 | 待实施 | View + API + E2E |
| FE-P0-07 | Model Provider | Provider/Model 配置与 Agent 使用关系 | 待实施 | View + API |
| FE-P0-08 | Audit | 跨领域操作证据查询与详情 | 待实施 | View + API |
| FE-P0-09 | Integration | Event → Delivery → Audit → Replay → Dead Letter | 待实施 | View + Real API |

### P1：稳定性与企业级体验

- FE-P1-01：统一 Loading / Empty / Error / Success / Permission 状态。
- FE-P1-02：全局错误分类与用户提示隔离，禁止 `error.message` / HTTP 原文直出。
- FE-P1-03：统一中文状态映射，未知技术值按“未知状态（技术值）”展示。
- FE-P1-04：清理 Element Plus 未解析组件警告。
- FE-P1-05：统一 PageHeader、Toolbar、MetricCard、DataTable、DetailPanel 等公共交互模式。
- FE-P1-06：建立 1440 / 1280 / 1024 / 768 / 390 响应式验收矩阵。
- FE-P1-07：补充核心页面 Playwright 用户旅程。

### P2：2.10-I 后端稳定后再实施

- Provider Registry / Health 前端化；
- Alert Rule 与 firing/recovery 生命周期；
- Notification Routing / Provider fallback；
- Notification SLO / Route Metrics；
- Runtime Alert Scheduler 运维视图；
- Prometheus / OpenTelemetry 配置与观测状态。

进入 P2 的前置条件：后端对应 Contract 稳定、Real API 可验收、持久化链路稳定、Runtime Acceptance 已明确完成范围。

### P3：平台化长期能力

- 全局搜索与快捷命令；
- 页面级权限矩阵；
- 通知中心；
- Dashboard 趋势与运营驾驶舱；
- 无障碍增强；
- 性能预算与资源优化；
- 主题 / 大屏 / 国际化。

## 4. 每个任务固定执行流程

```text
远端 main 同步
    ↓
确认 Backend Contract / 测试 / 验收状态
    ↓
检索现有前端 API、类型、页面、公共组件和测试
    ↓
确定最小业务切片
    ↓
实现 API Types
    ↓
实现 View / Component
    ↓
补充 Vitest
    ↓
本地 targeted test
    ↓
全量 npm test
    ↓
npm run build
    ↓
npm run test:gate
    ↓
必要时真实 Backend 联调 / E2E
    ↓
更新 frontend/docs 与项目状态
    ↓
一个原子提交进入 main
```

## 5. 完成定义

任务只有同时满足以下条件才能标记“完成”：

- 对应后端能力已确认稳定；
- API Contract 与 TypeScript 类型一致；
- 用户操作链路完整；
- Loading / Empty / Error / Success / Permission 状态完整；
- 用户可见文本使用通俗中文，技术标识保留在诊断需要的位置；
- 敏感信息不在浏览器明文回显；
- 相关 Vitest 通过；
- `npm run build` 通过；
- `npm run test:gate` 通过；
- 涉及真实后端时完成对应真实联调；
- 设计决策和实现细节已记录在 `frontend/docs`；
- 提交为单一功能的原子提交。

## 6. 当前执行指针

**当前任务：FE-P0-01 Agent 核心业务闭环。**

第一切片优先完善已经稳定存在的 Agent Version / Publish / Runtime Debug 数据关联，不提前接入尚未完成 Runtime Acceptance 的 2.10-I Notification 新能力。

下一任务必须从源码与后端 Contract 核对开始，不以文档更新代替实现。
