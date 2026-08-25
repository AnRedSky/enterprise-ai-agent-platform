# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration 已完成开发；Frontend Regression 与 Workflow Trigger Browser E2E 已由开发者本地实际通过；剩余 Browser / Backend / Real API Gate 与最终 Acceptance 汇总待完成。**
> 验收基线：`main`
> 评估日期：2026-08-25

## 1. 当前 Gate

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 本地 Gate 已通过：13 passed |
| Scheduler 持久化模型 | 本地 Migration Gate 已通过 |
| Alembic `0028_durable_scheduler_persistence` | 本地 `current` 为 head |
| 原子 lease claim / release | PostgreSQL Repository integration 已通过：2 passed |
| schedule slot 幂等 claim | PostgreSQL Repository integration 已通过 |
| WorkflowExecution 绑定 | Runtime Gate 已覆盖并通过 |
| Tenant / Organization scope | Repository lease/slot 与状态查询 tenant isolation 已覆盖 |
| Scheduler Runtime persistence 闭环 | 本地 Gate 已通过：4 passed |
| Scheduler API Contract / 状态可观测性 | 本地 Gate 已通过：6 passed |
| Misfire policy Runtime integration | 已完成开发，待最终汇总验收 |
| Frontend Regression Gate | 开发者本地实际通过：79 passed，production build 通过 |
| Workflow Trigger Browser E2E | **开发者本地实际通过：1 passed，脚本最终输出 `[PASS]`** |
| Organization Browser E2E | 待重新确认 |
| Model Provider Browser E2E | 待重新确认 |
| Backend default regression | 待重新确认 |
| Tenant Safe Real API acceptance | 待重新确认 |

## 2. Workflow Trigger Browser E2E 最终结果

开发者在当前 `main` 基线执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

实际结果：

```text
Running 1 test using 1 worker
✓ Workflow Trigger Governance completes the real scheduled browser contract (4.1s)
1 passed (5.0s)
[PASS] Phase 2.4 Workflow Trigger browser E2E gate completed.
```

本次真实浏览器验收覆盖：

1. 正式 `/workflows/triggers` 路由与真实登录 Session；
2. Trigger 类型正式 Select Contract；
3. 真实 Scheduled Trigger 创建并返回持久化实体；
4. Scheduler API 持久化状态确认；
5. Scheduler UI 异步初始化后的状态展示；
6. `timezone / interval_seconds / misfire_policy / catch_up_limit` 四字段 PostgreSQL 持久化 Config 最终断言。

因此 Workflow Trigger Browser Gate 现在可以标记为通过。

## 3. 历史失败与修复链路

本轮 Browser E2E 先后暴露并修复了以下工程问题：

```text
Workflow Version payload Contract
        ↓
正式 Workflow Trigger route Contract
        ↓
Browser Session / Auth Contract
        ↓
Element Plus Select pointer interception
        ↓
Trigger 创建 API 返回持久化实体
        ↓
Scheduler UI 异步初始化竞争
        ↓
持久化 Config 断言与正式 Contract 漂移
        ↓
Workflow Trigger Browser Gate 通过
```

这些修复均保持真实 Browser → Vue → Backend HTTP → PostgreSQL 链路，没有使用 Mock、JSON fixture、固定 sleep 或旧路径兼容垫片。

## 4. 后续 Acceptance 目标

至少覆盖：

- 多实例 lease 竞争；
- lease 过期抢占；
- 重复 schedule slot claim；
- misfire：skip / fire_once / bounded_catch_up；
- enabled / paused / disabled；
- WorkflowExecution 关联；
- Tenant Safe organization scope；
- Audit / Trace 关联；
- 服务重启后的 next_run_at / lease 恢复语义；
- Scheduler 状态 API 的 tenant isolation 与错误边界；
- Workflow Trigger 真实浏览器创建、状态查看、禁用、启用及持久化回读；
- Organization 与 Model Provider Browser E2E；
- Backend default regression 与 Tenant Safe Real API 最终确认。

## 5. 当前结论

**Phase 2.4 尚不能标记 Passed。**

Workflow Trigger Browser E2E 已通过，但最终阶段必须完成剩余 Browser / Backend / Real API Gate，并汇总 Scheduler 多实例、misfire、Execution、Audit / Trace、tenant isolation 与 restart recovery 的 Acceptance 结果后，才能形成 Phase 2.4 最终关闭结论。
