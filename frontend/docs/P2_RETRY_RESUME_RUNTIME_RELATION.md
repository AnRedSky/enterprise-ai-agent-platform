# P2：Retry / Resume → Parent Execution → Runtime 完整追踪

## 目标

把后端已经实现的 Retry / Durable Resume 生命周期字段完整落到 Runtime UI，形成“当前 Execution ↔ 来源 Execution ↔ 派生 Execution”的可追踪闭环。

## 后端事实 Contract

Workflow Execution API 已返回：

- `id`
- `retry_of_execution_id`
- `resume_of_execution_id`
- `resume_checkpoint_sequence`
- `status`

Retry 通过 `POST /workflows/executions/{execution_id}/retry` 创建新的 Execution；Resume 通过 `POST /workflows/executions/{execution_id}/resume` 创建新的 pending Execution。前端只消费这些字段，不推断关系，也不复制后端状态机。

## 前端实现

### 1. Runtime 类型补齐

`frontend/src/api/runtime.ts` 的 `Execution` 增加：

- `retry_of_execution_id?: string`
- `resume_of_execution_id?: string`
- `resume_checkpoint_sequence?: number`

### 2. Execution 详情关系卡

Runtime 打开 Workflow Execution 后，额外读取后端 Workflow Execution Detail，并展示：

- Retry 来源 Execution
- Resume 来源 Execution
- Resume checkpoint sequence
- 派生 Execution 列表

派生关系通过同一 Workflow 的 Execution 列表过滤：

- `retry_of_execution_id === current.id`
- `resume_of_execution_id === current.id`

### 3. 深链接

父/子 Execution 均通过真实 Execution ID 导航到：

`/runtime?execution_id=<id>&workflow_id=<workflow_id>&source=runtime-relation`

不会使用创建时间、状态或排序推测目标 Execution。

### 4. Retry / Resume 操作

操作仍然调用：

- `workflowApi.retryExecution`
- `workflowApi.resumeExecution`

接口返回的新 Execution ID 成功后立即进入新 Execution Runtime 详情，从而可以继续沿父链追踪。

## UX 规则

- 当前 Execution 是派生 Execution 时，关系卡明确标记“派生 Execution”。
- 没有父 Execution 时显示 `暂无`，不隐藏字段造成语义歧义。
- 没有子 Execution 时显示 `暂无派生 Execution`。
- ID 展示使用短 ID，但点击复制使用完整 ID。
- 后端错误信息不直接展示给用户。
- 父子导航统一通过 Runtime 页面，不新增独立的 Execution 页面。

## 验收标准

- [x] Retry Execution 能显示 `Retry 来源`。
- [x] Resume Execution 能显示 `Resume 来源`。
- [x] Resume Execution 能显示 `resume_checkpoint_sequence`。
- [x] 父 Execution 可以一键跳转。
- [x] 子 Retry / Resume Execution 可以一键跳转。
- [x] Retry / Resume 成功后自动进入真实新 Execution。
- [x] 不通过时间或状态推断父子关系。
- [x] 不复制后端 Retry / Resume 状态机。
- [x] 定向 Runtime 测试覆盖关系加载、导航和生命周期 API 调用。

## 下一阶段

继续实现 Trigger / Execution / Trace / Audit 的统一关联展示，并优先消费后端已有关联字段；只有后端 Contract 缺失时才记录为跨层待办，不在前端造字段。
