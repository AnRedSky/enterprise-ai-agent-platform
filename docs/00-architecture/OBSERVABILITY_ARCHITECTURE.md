# Observability Architecture

## 1. 目标

形成 Runtime Execution、Event、Trace、Token Usage、Error、Audit 的统一可追溯链路。

## 2. 核心关联标识

```text
request_id
trace_id
session_id
agent_id
agent_version
model_id
execution_id
```

## 3. Runtime 链路

```text
Request
 ↓
Execution
 ↓
Event / Span
 ↓
Model / Tool / Knowledge
 ↓
Result / Error
 ↓
Audit
```

每个阶段应保持可关联性，不以单独日志代替业务审计记录。

## 4. Query / Management

管理端应能够查询 Execution、Timeline、Audit，并支持 RBAC、Owner isolation、分页和过滤。前端失败、空结果、loading 状态均应有明确表现。

## 5. 治理原则

Observability 记录必须与 Runtime Contract 同步；涉及 Token Usage、Provider error、Execution state 的变化必须同时更新测试和验收文档。