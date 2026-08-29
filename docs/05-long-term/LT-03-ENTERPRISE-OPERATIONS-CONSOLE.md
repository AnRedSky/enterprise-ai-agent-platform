# LT-03 Enterprise Operations Console

## 1. 目标
形成面向企业运维人员的统一管理后台，覆盖任务、Workflow、Agent、Scheduler、Worker、失败任务和运行状态，而不仅是当前的管理与调试 UI。

## 2. 当前状态
**待立项。** 当前已有 Vue 管理/调试界面及治理 UI，但完整 Operations Console 尚未形成。

## 3. 主要缺口
- 全局运行态势；
- Workflow/Execution/Frontier/Delegation 运维视图；
- Scheduler/Worker 状态与租约诊断；
- 失败任务重试、取消、恢复、Replay 的受控入口；
- Tenant/Organization 管理运营视图；
- Audit/Trace 查询与关联；
- 权限分级、操作审批和高风险操作保护；
- 批量运维与审计留痕。

## 4. 长期拆解
Operations 信息架构 → API Contract → Runtime 运维接口 → Vue 页面 → 权限与审计 → Browser E2E → 发布验收。

## 5. 完成判定
关键后台对象可查询、诊断和执行受治理操作；高风险操作有权限/审计；真实 Backend + Frontend + Browser 验收通过。
