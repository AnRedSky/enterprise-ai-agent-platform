# P2 Workflow / Trigger / Runtime 前端实施进度

## 本阶段目标

形成 `Workflow → Version → Trigger → Execution → Runtime` 的完整前端业务闭环，优先消费后端已经实现并稳定提供的 HTTP Contract，不在前端虚构后端尚未提供的生命周期能力。

## 已实施

### Workflow 生命周期

- Workflow 详情支持名称与描述编辑。
- 已归档 Workflow 进入只读状态。
- Workflow 删除仅开放给 `draft` 状态；`published` / `archived` 明确阻止危险操作。
- 已发布 Workflow 不覆盖当前生效定义；流程定义修改通过新 Version 完成切换。

### Trigger Governance

- Trigger 支持创建、编辑、启用、禁用、删除。
- 编辑时 Trigger 类型不可变，避免把既有 Scheduler/Webhook 资源隐式转换成另一类资源。
- Webhook 编辑时 Secret 留空表示保持现有 Secret；只有显式填写新 Secret 才更新认证凭据。
- 启用 Trigger 前要求 Workflow 已发布；前端只做入口约束，后端仍是最终权威。
- 启用/禁用均要求确认；删除属于危险操作，必须二次确认并明确提示会解除对应入口/调度配置。
- Scheduled Trigger 继续读取后端 Scheduler 持久化状态，不在浏览器侧模拟调度。

### Trigger → Runtime

- Manual Trigger Invoke 成功后直接跳转 `/runtime`，携带 `execution_id`、`workflow_id`、`source=workflow-trigger`。
- Invoke 使用前端生成的 `Idempotency-Key`，降低重复点击造成重复执行的风险。
- Runtime 负责按 Execution ID 自动定位真实执行上下文。

## 当前生命周期状态规则

| 资源 | 状态 | 前端入口 |
|---|---|---|
| Workflow | draft | 可编辑、创建版本、发布、删除 |
| Workflow | published | 可编辑元数据、创建新版本；删除受限 |
| Workflow | archived | 只读 |
| Trigger | enabled | 可编辑、禁用、删除；Manual 可 Invoke |
| Trigger | disabled | 可编辑、启用、删除；不可 Invoke |

> 前端状态约束只负责用户入口和 UX；最终合法性仍由后端 Contract 决定，不能将前端判断视为安全边界。

## 本轮设计决策

1. **Trigger 类型稳定性**：编辑只允许修改名称与 Config，不允许直接改变 trigger_type。
2. **认证凭据最小暴露**：Webhook Secret 不回显；编辑留空保持原凭据，重新生成后才发送新 Secret。
3. **启用前置条件**：未发布 Workflow 不允许从前端启用 Trigger，避免产生无法运行的入口。
4. **危险操作显式确认**：启用、禁用、删除均提供确认反馈；删除使用更明确的危险操作文案。
5. **后端最终裁决**：前端不复制 Scheduler、Worker 或执行状态机，只根据已知 Contract 做 UX 约束。

## 专项测试计划

主线开发完成前不执行全量 `npm test`。本阶段专项测试应覆盖：

- Trigger 创建 / 编辑成功与校验失败。
- Manual / Scheduled / Webhook 三种类型的 Config 展示与编辑。
- Webhook Secret 保持、更新和非法长度校验。
- 已发布 Workflow 才允许启用 Trigger；未发布 Workflow 的启用入口被阻止。
- 启用、禁用确认的确认与取消路径。
- 删除危险操作确认的确认与取消路径。
- disabled Manual Trigger 不可 Invoke。
- Invoke 成功后携带 Execution 上下文进入 Runtime。
- Invoke 失败时不发生 Runtime 跳转。

## 下一阶段

1. 完成 Workflow 页面版本发布后的 Trigger 可用性联动展示。
2. 补齐 Webhook Trigger 的调用入口、请求事实展示及失败处理，不在浏览器直连业务目标。
3. 将 Scheduler Trigger 的启停结果与 Runtime Execution 历史建立可追溯关联。
4. 完成 P2 Workflow / Trigger / Runtime 主线后，再按阶段执行专项测试，最后执行完整回归与手动验收。

## 完成标准

只有当 Workflow 创建/编辑/删除、版本创建/发布、Trigger 创建/编辑/启停/删除与调用、Execution 创建/运行/取消/重试/恢复、Runtime 查询和 Trace 均能通过真实 API Contract 连通，并具备 Loading/Empty/Error/Success 状态后，P2 才允许标记完成。
