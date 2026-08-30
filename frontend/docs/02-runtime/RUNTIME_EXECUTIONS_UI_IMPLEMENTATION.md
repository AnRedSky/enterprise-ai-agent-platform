# Runtime 运行记录前端深化

## 本轮目标

在不引入后端尚未提供的能力前提下，补齐 Runtime 查询页面对现有查询 Contract 的使用，降低运维人员定位执行记录的成本。

## 后端 Contract 对齐

当前 Runtime `/executions` 已支持：

- `status`
- `agent_id`
- `trace_id`
- `request_id`
- `session_id`
- `started_from`
- `started_to`
- `page`
- `page_size`

本轮前端将其中高频运维筛选条件直接暴露为查询控件，并继续复用既有 `runtimeApi.executions()`，不改变 API 层协议。

## UI 设计决策

1. 状态、智能体、链路、请求 ID 采用文本筛选，适合直接粘贴技术标识。
2. 时间范围采用日期时间范围选择器，统一转换为 ISO-8601 后提交后端。
3. 查询和重置都会回到第 1 页，避免筛选条件改变后仍停留在不存在的页码。
4. 保留现有执行详情 Drawer、时间线和 Workflow Trace，不改变已有用户路径。
5. 桌面端使用两列筛选布局，小屏自动降为单列，避免筛选栏横向溢出。
6. 后端未提供的筛选能力不在前端虚构；`session_id` 当前保留在详情展示中，待后续需要高频检索时再增加专用输入。

## 完成标准

- 查询条件能够映射到正式 Runtime API Contract；
- 查询、重置、分页行为一致；
- 不暴露后端原始异常文本；
- 不改变执行详情既有能力；
- P2 阶段测试入口继续覆盖 Runtime 测试；
- 最终全量测试仍按主线完成后的统一 Gate 执行。

## 验证计划

本轮开发阶段不执行全量 `npm test`。主线完成后，通过 P2 阶段脚本验证 Runtime 页面，再进入全量 Frontend Gate 与 Browser E2E。
