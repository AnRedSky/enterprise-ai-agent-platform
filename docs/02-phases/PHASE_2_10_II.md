# Phase 2.10-II — Enterprise Operations Console / Operator Governance

## 1. 目标

在 Phase 2.10-I 完成 Runtime Notification、Metrics、SLO、Audit 与统一 Runtime Acceptance 后，继续推进 LT-03 Enterprise Operations Console，将现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力收敛为可治理的企业运维工作台。

本阶段不重新实现已经稳定的 Runtime Notification、Metrics、Telemetry、Provider 或 Workflow 状态机，而是围绕现有 Backend Contract 建立统一的运维操作边界、诊断关联和高风险操作保护。

## 2. 当前状态

**开发中。**

Phase 2.10-I 已根据本地实际 Real Gate 反馈完成 Runtime Notification Lifecycle 收口；当前正式下一阶段为 LT-03 的 Operations Console 治理切片。

## 3. 第一切片：Operator Action Governance

### 3.1 目标

为 Runtime / Workflow / Trigger 运维操作建立统一的操作治理 Contract，避免前端自行判断权限、状态或重复实现生命周期规则。

### 3.2 操作边界

```text
查询 / 诊断
    ↓
操作可用性查询
    ↓
权限 + 当前状态校验
    ↓
操作执行
    ↓
幂等结果
    ↓
Operational Audit
```

第一批纳入：

- Workflow Execution：Run / Cancel / Retry / Resume；
- Trigger：Enable / Disable / Delete / Invoke；
- Runtime：Execution 诊断深链；
- Audit：操作结果与失败原因关联。

### 3.3 强制规则

1. Tenant scope 必须由后端身份上下文决定，前端不得提交并决定目标 Tenant。
2. 前端不得复制 Workflow / Trigger 状态机；操作是否允许由 Backend Contract 决定。
3. 高风险操作必须有明确的操作确认语义，并记录 actor、action、resource、outcome。
4. 可重试操作必须具备明确幂等边界，避免重复创建 Execution 或重复修改 Trigger。
5. 操作失败不得把数据库异常、HTTP 原文或内部堆栈直接暴露给用户。
6. 查询与操作保持职责分离；诊断页面不得直接修改数据库事实。
7. 所有操作必须保留真实 resource ID，并能够回到 Runtime / Audit 诊断路径。

## 4. 后续切片

### II-02 Global Runtime Operations

- 全局 Execution / Workflow / Worker / Scheduler 运行态势；
- 失败、运行中、等待、恢复中的统一视图；
- 按 Tenant / Workflow / Agent / Trigger / Execution 关联查询。

### II-03 Worker / Scheduler Diagnostics

- Worker lease / claim / concurrency 状态；
- Scheduler loop / trigger / misfire 状态；
- 失败恢复与运行态诊断；
- 不暴露内部连接和 Secret。

### II-04 Audit / Trace Correlation

- Execution → Trace → Audit 双向关联；
- Operator Action → Audit → Execution 关联；
- 稳定分页、筛选和深链。

### II-05 Controlled Batch Operations

- 批量 Retry / Cancel / Replay 等高风险操作；
- 权限、确认、幂等、部分失败结果和审计；
- 禁止前端复制批量业务规则。

## 5. 完成判定

第一切片必须同时满足：

- Backend Contract、Service、Repository、Audit 规则完成；
- tenant boundary 有 unit + Real API 覆盖；
- 高风险操作具备权限/状态校验与审计事实；
- Frontend 使用 Backend Contract，不复制业务规则；
- Frontend Vitest 与 Build 通过；
- Backend Regression 与 Real API Gate 通过；
- 范围需要时执行 Browser E2E；
- 测试 Gate 不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，测试数据自动生成和清理。

## 6. 开发顺序

```text
Operator Action Contract
        ↓
Backend Domain / API Contract
        ↓
Unit + Integration + Real API
        ↓
Frontend API Types
        ↓
Operations UI
        ↓
Frontend Regression / Build
        ↓
Backend Regression / Real API
        ↓
Browser E2E
        ↓
Phase Acceptance
```
