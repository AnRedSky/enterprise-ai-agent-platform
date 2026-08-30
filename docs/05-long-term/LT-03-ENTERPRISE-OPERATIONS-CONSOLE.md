# LT-03 Enterprise Operations Console

## 1. 目标
形成面向企业运维人员的统一管理后台，覆盖任务、Workflow、Agent、Scheduler、Worker、失败任务和运行状态，而不仅是当前的管理与调试 UI。

## 2. 当前状态
**Phase 2.10-II 开发中。**

Phase 2.10-I 已完成 Runtime Operations Console 第一切片及 Runtime Notification Lifecycle 验收；当前进入 Operations Console 的统一 Operator Action Governance。

## 3. 已具备能力
- Runtime Execution 查询、详情、Trace、Audit 深链；
- Workflow Execution 的 Run / Cancel / Retry / Resume 生命周期入口；
- Workflow Trigger 的创建、编辑、启停、删除、Invoke 与 Scheduler 状态入口；
- Agent 发布版本与对话调试入口；
- Runtime Notification / Metrics / SLO / Audit 运维查询；
- Tenant-scoped Runtime Operations API 与统一测试 Gate。

## 4. 当前缺口
- 统一 Operator Action Contract；
- 操作权限与当前状态的后端可用性判断；
- 高风险操作确认、幂等与审计统一治理；
- 全局 Runtime / Workflow / Worker / Scheduler 运行态势；
- Worker lease / claim / concurrency 诊断；
- Scheduler loop / trigger / misfire 诊断；
- Execution → Trace → Audit 与 Operator Action → Audit → Execution 统一关联；
- 批量运维与部分失败结果治理。

## 5. 当前阶段入口
正式 Phase：`docs/02-phases/PHASE_2_10_II.md`

第一切片：**Operator Action Governance**。

## 6. 完成判定
关键后台对象可查询、诊断和执行受治理操作；高风险操作具有权限、状态、幂等和审计保护；真实 Backend + Frontend + Browser 验收通过。
