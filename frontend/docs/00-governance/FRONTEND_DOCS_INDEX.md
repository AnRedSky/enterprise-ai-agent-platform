# 前端文档中心

> `frontend/docs` 是前端工程设计、实现、验证、回归与长期规划的统一文档中心。项目级规则以 `docs/01-governance/DEVELOPMENT.md` 为最高约束；本目录只维护前端领域的补充规则与工程事实。

## 文档目录

- `00-governance/`：工程规则、文档治理、测试执行规则。
- `01-architecture/`：信息架构、App Shell、Dashboard 与长期 UI 设计。
- `01-design/`：UI Gap Audit、页面补齐计划与设计决策。
- `02-runtime/`：Runtime Execution、可观测性、深链与运行时加固。
- `03-agent/`：Agent 调试与相关交互设计。
- `04-workflow/`：Workflow 生命周期与 Execution 联动。
- `05-integration/`：Integration Event Console、Webhook Delivery。
- `06-ui-text/`：用户可见文本规范及迁移记录。
- `07-testing-regression/`：回归、发布加固和测试事实。
- `08-p2-planning/`：P2 Runtime / Trigger / Retry / Trace / Audit 规划。
- `09-history/`：历史阶段状态、评估与后端对齐记录。

## 核心治理文档

| 文档 | 职责 |
|---|---|
| `00-governance/FRONTEND_DEVELOPMENT_GUIDELINES.md` | 前端实现、测试、文档和提交的工程规范 |
| `00-governance/FRONTEND_DOCS_INDEX.md` | 文档中心索引与当前主线 |
| `01-design/UI_GAP_AUDIT_PLAN.md` | 当前全站 UI Gap Audit、P0/P1 任务台账、执行状态与原子任务队列 |
| `07-testing-regression/` | 实际测试、回归和发布验证事实 |

## 维护规则

1. 新规则只写入唯一规范文档，不在功能文档复制规则。
2. 新任务优先更新已有主线文档，禁止为每次小修改新增日期文件。
3. 历史事实可以保留，但不能继续作为当前规则来源。
4. 文档状态必须与代码、测试和 Backend Contract 一致。
5. 文档整理应与相关代码/测试作为同一原子交付单元提交。
6. 任务台账必须记录实际状态、下一原子任务和验证事实；未执行的测试不得记录为通过。

## 当前主线

当前主线：**Phase 2.10-II Enterprise Operations Console / Operator Governance**。

Phase 2.10-I Runtime Notification Lifecycle、Metrics、Telemetry、Audit 已由 Backend Real Gate 收口；前端现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力作为本阶段统一操作治理的既有入口，不再重复实现相同业务 Contract。

第一前端工作项：对齐 Backend Operator Action Contract，统一展示操作可用性、权限拒绝、状态冲突、幂等结果和审计关联；前端不得复制 Workflow / Trigger 状态机或后端权限判断。

现有 P1.1 Runtime 深链、Agent 调试上下文、Workflow 生命周期、Trigger 操作和 Audit 可观测性继续作为回归基线；后续增强必须围绕统一 Operator Action Governance 进行。

当前具体执行采用 `01-design/UI_GAP_AUDIT_PLAN.md` 的 P0/P1 队列推进，优先完成 Runtime / Workflow / Agent，再进入 Knowledge / Tools / Organizations / Model Providers / Integrations / Operations / Audit，最后执行全站一致性回归。
