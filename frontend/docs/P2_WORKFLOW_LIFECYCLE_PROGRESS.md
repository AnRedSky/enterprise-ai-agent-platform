# P2 Workflow 生命周期前端实施进度

## 本阶段目标

形成 `Workflow → Version → Trigger → Execution → Runtime` 的完整前端业务闭环，优先消费后端已经实现并稳定提供的 HTTP Contract，不在前端虚构后端尚未提供的生命周期能力。

## 本轮已实施

### Workflow 生命周期

- Workflow 详情接入 `PATCH /workflows/{workflow_id}`，支持名称与描述编辑。
- 已归档 Workflow 进入只读状态，不允许编辑、创建版本或发布。
- Workflow 删除仅开放给 `draft` 状态；`published` / `archived` 前端明确阻止删除并给出原因。
- 删除操作必须经过危险操作确认，并在成功后清理当前选择、版本和运行记录状态。
- 已发布 Workflow 不覆盖当前生效定义；流程定义修改统一通过创建新 Version，再发布新 Version 完成切换。
- 发布按钮按 Workflow / Version 状态约束：已归档 Workflow、已发布 Version、当前生效 Version 均不可重复发布。

### Trigger → Runtime

- Manual Trigger Invoke 成功后，前端直接跳转 `/runtime`，携带 `execution_id`、`workflow_id` 和 `source=workflow-trigger` 查询参数。
- Invoke 继续使用前端生成的 `Idempotency-Key`，避免重复点击产生非预期重复执行。
- Runtime 页面已具备工作流 Trace 展示能力，后续继续接入查询参数自动定位 Execution。

## 生命周期状态规则

| 状态 | 编辑元数据 | 创建新版本 | 发布版本 | 删除 |
|---|---:|---:|---:|---:|
| draft | 是 | 是 | 是 | 是 |
| published | 是 | 是 | 按版本约束 | 否 |
| archived | 否 | 否 | 否 | 否 |

> 前端状态约束只负责用户入口和 UX；最终合法性仍由后端 Contract 决定，不能将前端判断视为安全边界。

## 本轮设计决策

1. **删除优先保守**：已发布或已归档资源不提供删除入口，避免误操作破坏可追溯生命周期。
2. **发布不可逆入口需确认**：发布属于影响运行环境的治理操作，必须二次确认。
3. **已发布定义不原地编辑**：通过新 Version 保证当前生效版本稳定，并保留版本审计链。
4. **Trigger Invoke 以 Execution 为结果实体**：调用成功后不在 Trigger 页面停留展示临时结果，而是直接进入 Runtime Execution 上下文。
5. **后端是最终状态机**：前端只做已知状态的按钮约束，不复制后端状态机、Scheduler 或 Worker 规则。

## 专项测试计划

主线开发完成前不执行全量 `npm test`。本阶段完成后新增/维护专项测试覆盖：

- Workflow 编辑成功、校验失败、后端失败。
- draft 可删除；published / archived 删除入口受限。
- 删除危险操作确认的确认与取消路径。
- 已发布 Version / 当前生效 Version 不重复发布。
- archived Workflow 不允许创建新 Version。
- Manual Trigger Invoke 成功后携带正确 Execution 上下文跳转 Runtime。
- Invoke 失败时不发生错误跳转。

## 下一步

1. Trigger 页面补齐 Trigger 名称与 Config 更新入口，并继续遵循后端状态约束。
2. Runtime 接收 `execution_id` 查询参数并自动打开对应 Execution 详情，形成真正的 Trigger → Runtime 直接定位。
3. Workflow 页面补齐版本发布后的 Trigger 可用性联动展示。
4. 完成 P2 Workflow / Trigger / Runtime 主线后，再按阶段执行专项测试，最后执行完整回归与手动验收。

## 完成标准

只有当 Workflow 创建/编辑/删除、版本创建/发布、Trigger 管理与调用、Execution 创建/运行/取消/重试/恢复、Runtime 查询和 Trace 均能通过真实 API Contract 连通，并具备 Loading/Empty/Error/Success 状态后，P2 才允许标记完成。
