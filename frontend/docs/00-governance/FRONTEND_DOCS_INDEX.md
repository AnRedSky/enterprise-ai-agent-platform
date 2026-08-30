# 前端文档中心

> `frontend/docs` 是前端工程设计、实现、验证、回归与长期规划的统一文档中心。项目级规则以 `docs/01-governance/DEVELOPMENT.md` 为最高约束；本目录只维护前端领域的补充规则与工程事实。

## 文档目录

- `00-governance/`：工程规则、文档治理、测试执行规则。
- `01-architecture/`：信息架构、App Shell、Dashboard 与长期 UI 设计。
- `02-runtime/`：Runtime Execution、可观测性、深链与运行时加固。
- `03-agent/`：Agent 调试与相关交互设计。
- `04-workflow/`：Workflow 生命周期与 Execution 联动。
- `05-integration/`：Integration Event Console、Webhook Delivery。
- `06-ui-text/`：用户可见文本规范及迁移记录。
- `07-testing-regression/`：回归、发布加固和测试事实。
- `08-p2-planning/`：P2 Runtime / Trigger / Retry / Trace / Audit 规划。
- `09-history/`：历史阶段状态、评估与后端对齐记录。

## 维护规则

1. 新规则只写入唯一规范文档，不在功能文档复制规则。
2. 新任务优先更新已有主线文档，禁止为每次小修改新增日期文件。
3. 历史事实可以保留，但不能继续作为当前规则来源。
4. 文档状态必须与代码、测试和 Backend Contract 一致。
5. 文档整理应与相关代码/测试作为同一原子交付单元提交。

## 当前主线

当前主线：**P1.1 深度交互与可观测性工作台**。

本轮推进 **P1.3 Runtime ↔ Workflow 生命周期双向深链**：Workflow 生命周期页面可从真实 `workflow_id` 恢复上下文；Runtime 在存在真实 Workflow 上下文时可返回生命周期页面。详见 `04-workflow/P1.3-RUNTIME-WORKFLOW-BIDIRECTIONAL-DEEPLINK.md`。

后续继续完成 Agent 调试上下文、Trigger 操作面板及 P1.1 核心闭环验收。
