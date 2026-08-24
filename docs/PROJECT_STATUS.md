# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration Gate 已通过；Tenant Safe Real API 仍有 3 个失败，当前不能标记 Passed。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮基于远端 `main` 最新提交 `2bb1d4a` 继续开发。该提交已修复当前 interval slot 被错误标记为 recovery 的边界问题，并新增对应单元测试。随后开发者本地实际执行结果确认 Scheduler Tenant / Misfire Gate 已全部通过，但 Tenant Safe Real API 仍暴露新的运行时验收问题。

开发者本地最新实际结果：

```text
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"：APP_IMPORT_OK
Scheduler targeted tests：34 passed
04_scheduler_tenant_misfire_gate.ps1：22 misfire unit tests、3 PostgreSQL tenant integration、6 API Contract、395 Backend regression 均通过；3 skipped，35 deselected
01_run_real_api_tests_tenant_safe.ps1：35 个测试中 3 个失败
```

当前 Real API 三个失败已经完成初步根因分类：

1. 后台 Scheduler 生命周期场景没有在验收窗口内产生预期当前槽位 Execution，需要确认真实 API 服务是否使用带 `scheduler_enabled=true` 的当前进程配置，并将后台生命周期启动作为 Gate 前置条件显式验证。
2. Runtime 持久化的 `input_data.scheduled_slot` 当前写入完整 `scheduled:{trigger_id}:{slot}` 幂等键，但 Real API Contract 要求这里记录数值 interval slot；本轮代码已修复 Runtime 生成路径，改为持久化数值 slot，同时继续使用完整 key 作为 `idempotency_key`。
3. Recovery slot 同样受 `scheduled_slot` 元数据类型问题影响；Recovery 判断本身已使用统一 `is_recovery_slot()`，历史槽位 true、当前槽位 false 的规则不再依赖简单 `planned_at < now`。

## Phase 2.4 当前推进

Durable Scheduler 已完成 Contract-first + Persistence + Runtime + Scheduler 状态 API 第一阶段。

当前收口顺序：

1. **Scheduler Runtime metadata contract**
   - Execution 的正式幂等键继续由 `ScheduledTriggerScheduler.idempotency_key()` 唯一生成；
   - `input_data.scheduled_slot` 记录数值 interval slot；
   - `input_data.recovery` 只由统一 `is_recovery_slot()` 判断；
   - 不新增第二套 slot key 或 recovery 计算实现。

2. **真实后台生命周期验收**
   - Tenant Safe Real API Gate 必须明确验证 Scheduler 进程实际启用；
   - 真实 HTTP Trigger 创建 / 更新后，必须能从 PostgreSQL 读取 Scheduler 产生的 Execution；
   - 不以直接调用 Runtime 替代后台生命周期验收，但允许将直接 Runtime tick 作为确定性补充测试。

3. **后续 Runtime production acceptance**
   - 多实例 lease；
   - misfire / catch-up；
   - Execution 状态；
   - Audit / Trace；
   - 服务重启恢复。

## 开发准则本轮增强

`docs/01-governance/DEVELOPMENT.md` 本轮新增并明确：

- 新增业务能力前必须先检索已有领域实现，避免重复 Service / Repository / Runtime / Provider / 工具函数；
- 同一业务规则只能保留一个正式计算 / 校验入口，测试不得复制生产算法形成第二套实现；
- 模块、类、函数 / 方法必须按实际复杂度补充中文职责、边界、参数、返回值及副作用说明；
- 时间槽、幂等、租约、misfire、tenant boundary、状态机等非显然规则必须说明设计原因与边界条件；
- Real API Gate 必须区分后台生命周期验收与确定性 Runtime 补充测试，不能使用 Mock / JSON fixture 替代真实持久化业务流程；
- 依赖本地服务的自动化 Gate 必须明确服务、环境变量、数据库状态、启动命令和失败条件。

## 当前禁止事项

- 不标记 Phase 2.4 Passed；
- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支。
