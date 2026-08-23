# Phase 2.4 — Durable Scheduler

> 状态：**已确认进入 Contract 设计，不进入业务代码实现**
> 评估日期：2026-08-23
> 优先级：**P1**
> 产品主题：Durable Scheduler

## 1. 方案决策

Phase 2.4 确认为下一项正式工作，但采用“**Contract-first + MVP 边界 + 可替换实现**”方案：

- 首先冻结 Scheduler 领域 Contract，再进入 Migration、Backend、Real API。
- 第一版只解决企业定时 Workflow 的持久化、恢复、租约、多实例 ownership、misfire、幂等和审计追踪。
- 不在 Phase 2.4 首版引入 MQ/Kafka、Temporal、独立 Scheduler 服务、复杂 DAG 或通用分布式工作流引擎。
- Scheduler 依赖 PostgreSQL 持久化状态；租约实现优先复用 PostgreSQL 原子更新/行锁，避免新增基础设施依赖。
- `next_run_at` 持久化为 UTC；原始时区作为调度配置的一部分保存，计算时明确时区语义。
- 后续如吞吐或多区域场景证明 PostgreSQL scheduler 无法满足要求，再独立评估 MQ/Event Bus 或专用调度基础设施，不提前绑定技术方案。

## 2. 为什么现在优先做 Scheduler

当前平台已经具备 Workflow、Execution、Trigger、可靠性、Audit/Trace 和 PostgreSQL 持久化基础能力；Durable Scheduler 可以直接补齐现有 Scheduled Trigger 的长期运行可靠性，而不需要先扩大产品边界。

相比 Advanced Workflow、Event Infrastructure、Multi-Agent 和 Marketplace，Scheduler 的业务边界更清晰、现有代码复用度更高、验收链路更短，因此作为 P1 下一阶段最具执行确定性的能力。

## 3. MVP Contract

### 3.1 调度对象

首版调度对象限定为已发布 Workflow 的 Scheduled Trigger。

必须能够持久化：

- `trigger_id`
- `workflow_id`
- `enabled`
- `timezone`
- `schedule_expression`
- `next_run_at`
- `last_run_at`
- `last_execution_id`
- `lease_owner`
- `lease_expires_at`
- `misfire_policy`
- `updated_at`

不新增通用 Job/Task 产品概念，除非后续产品需求明确要求。

### 3.2 `next_run_at` 与时区

- `next_run_at` 为数据库中的 UTC 时间。
- `timezone` 保存用户配置的 IANA 时区名称。
- 调度表达式按 `timezone` 解释，再转换为 UTC 保存。
- 时间计算必须使用可测试的 clock abstraction，不直接依赖不可控系统时间。
- 夏令时产生的歧义/不存在时间必须有确定规则并纳入 Contract Test。

### 3.3 多实例 Lease / Ownership

- 多个 Scheduler worker 可以同时轮询数据库，但同一调度槽位只能由一个 owner 获得执行权。
- Lease 必须包含 owner 与过期时间。
- 获取 lease 必须是数据库原子操作，不允许“先查询、后更新”的非原子抢占。
- Lease 未过期时其他实例不得执行该槽位。
- Lease 过期后允许其他实例抢占。
- owner 丢失连接后不得继续无限持有执行权。

### 3.4 重复执行与幂等

首版定义稳定的 `schedule_slot_key`，由 `trigger_id + 计划执行时间槽` 形成。

- 同一个 `schedule_slot_key` 最多产生一个有效 WorkflowExecution。
- 数据库唯一约束负责最终去重，不能只依赖内存锁。
- Lease 重试、进程重启、网络超时都不得导致同一槽位无限重复创建执行记录。
- WorkflowExecution 仍保留自身 execution identity；Scheduler 幂等键只负责调度入口去重。

### 3.5 Misfire Policy

首版支持三个明确策略：

| 策略 | 语义 |
|---|---|
| `skip` | 错过的调度槽位直接跳过，计算下一个未来槽位 |
| `fire_once` | 无论错过多少槽位，只补执行一次，然后进入下一个未来槽位 |
| `catch_up` | 在受控上限内逐槽补执行；超过上限的槽位不无限追赶 |

`catch_up` 必须有最大补偿次数配置，防止服务长时间停止后形成执行风暴。

### 3.6 状态转换

首版状态至少覆盖：

```text
enabled
  ↓ pause
paused
  ↓ resume
enabled

enabled
  ↓ disable
disabled
```

- `paused` 不创建新的 WorkflowExecution，但保留当前调度状态。
- `disabled` 停止调度并清理/失效 lease。
- 恢复后按照明确的 misfire policy 决定是否补偿。
- 删除 Trigger 时不得留下可继续执行的 lease。

### 3.7 Audit / Trace

每次 scheduler ownership、misfire decision、execution creation 和状态变化必须可追踪。

至少能够关联：

```text
trigger_id
schedule_slot_key
scheduler_owner
workflow_execution_id
request_id / trace_id（进入 Runtime 后）
```

Scheduler 本身不得记录 Secret；日志与 Audit 不得泄露 credential、token 或 endpoint 敏感凭据。

## 4. 推荐实现顺序

```text
Phase 2.4 Contract
      ↓
Backend Domain + API Contract
      ↓
PostgreSQL Migration
      ↓
Unit / Integration / API Contract tests
      ↓
Scheduler persistence + lease
      ↓
Misfire + idempotency
      ↓
Real API Gate
      ↓
Backend Regression Gate
      ↓
Frontend API / UI（只有存在明确用户操作范围时）
      ↓
Browser E2E（只有存在对应 UI 用户链路时）
```

## 5. 暂不纳入范围

以下内容保持候选状态，不因为 Phase 2.4 自动进入开发：

- MQ/Kafka/Event Bus
- Temporal 等独立 Workflow Engine
- 独立 Scheduler 微服务
- 跨区域 Scheduler
- 高级 DAG / Saga / Compensation
- 通用任务市场
- Multi-Agent
- Marketplace

## 6. 进入代码开发的 Gate

只有以下条件全部确认，才允许创建 Migration 和业务代码：

1. Contract 字段与状态语义确认；
2. `next_run_at` / timezone / clock 语义确认；
3. Lease ownership、过期与抢占确认；
4. misfire、幂等和重复执行边界确认；
5. paused / enabled / disabled 转换确认；
6. Audit / Trace 关联字段确认；
7. PostgreSQL migration 与 Real API acceptance 场景确认。

> 本文件只确认 Phase 2.4 的可执行方案，不代表 Scheduler 业务代码已经实现或验收通过。
