# Phase 1.5-F / 003 Workflow Runtime 可观测性

## 目标

在已有 Workflow Execution 状态机、Node Execution、Audit 与 Trace 持久化基础上，补齐真实业务闭环：运行结束后，调用方能够按 Execution 查询完整的运行时间线与 Workflow Trace，而不需要直接访问数据库或拼接 Audit 数据。

## 后端 Trace 读取接口

`GET /api/v1/runtime/executions/{execution_id}/trace`

接口沿用现有 Execution RBAC 边界：

- tenant 必须匹配；
- 非 admin 只能查询自己的 Execution；
- admin 可以查询本 tenant 内的 Execution；
- Trace Event 同时校验 `tenant_id` 与 `execution_id`。

返回字段包括：

- `event_type` / `status`
- `node_id`
- `trace_id`
- `actor_id`
- `data`
- `error_code` / `error_message`
- `created_at`
- workflow / version / execution / tenant 标识

## 前端真实业务闭环

Runtime Execution 列表中的一行打开后，现有 Execution Timeline 与新增 Workflow Trace 同时加载：

```text
Execution
  ├── Runtime Timeline
  │    ├── span_type
  │    ├── status
  │    ├── duration
  │    └── retrieval metadata
  └── Workflow Trace
       ├── event_type
       ├── node_id
       ├── status
       ├── error_code / error_message
       └── data
```

前端通过 `runtimeApi.executionTrace()` 调用 Trace 接口，不重新定义 Trace 数据模型，并在同一次 Execution 打开动作中与 Timeline 并行加载。

## 现有 Runtime 事件链

Execution 创建、状态转换、Node 状态转换以及终态治理已经通过 `WorkflowGovernanceService` 写入 Audit / Trace；读取层只负责按既有权限提供数据，不新增第二套观测模型。

## 验收原则

继续使用既有 `tests/api_contract`、`tests/integration`、`tests/unit` 以及完整 backend regression 入口；前端继续使用既有 Vitest 测试入口，不创建新的测试脚本入口，也不把开发脚本与测试脚本混用。

本阶段继续保持前端构建原则：业务路由 lazy loading、Element Plus 按需注册，Rollup 仅保留稳定且无循环风险的 vendor chunk，不人为继续拆分 vendor。

## 下一步

在完成本次 Execution Timeline + Workflow Trace 闭环并通过手工验收后，再进入执行治理增强：重点考虑失败节点定位、重试/取消结果展示以及执行级 Audit 联动；仍优先复用现有数据模型和权限服务。
