# Phase 1.5-F / 003 Workflow Runtime 可观测性

## 目标

在已有 Workflow Execution 状态机、Node Execution、Audit 与 Trace 持久化基础上，补齐真实业务闭环：运行结束后，调用方能够按 Execution 查询完整的运行时间线，而不需要直接访问数据库或拼接 Audit 数据。

## 本次实现

新增：

`GET /api/v1/workflows/executions/{execution_id}/trace`

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

## 现有 Runtime 事件链

Execution 创建、状态转换、Node 状态转换以及终态治理已经通过 `WorkflowGovernanceService` 写入 Audit / Trace；本次只补齐读取入口，不新增第二套观测模型。

## 验收原则

继续使用既有 `tests/api_contract` 与完整 backend regression 入口，不创建新的测试脚本入口，也不把开发脚本与测试脚本混用。

下一阶段可在此接口之上继续建设前端 Execution Timeline / Runtime Observability UI，并优先复用现有 Trace 数据，而不是重新实现一套运行日志。
