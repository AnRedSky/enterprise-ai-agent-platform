# 2026-08-26 Worker Lease 过期后 Heartbeat 续租边界

## 1. 问题

Worker heartbeat 原实现只校验 `worker_owner` 与 Execution 状态，没有把 `worker_lease_expires_at > now` 作为续租前置条件。

因此存在以下竞态：

```text
T0  Worker A claim
    lease = T0 + 60s

T1  A heartbeat 因数据库瞬态异常未及时执行

T2  lease 已过期
    A ownership 按租约语义已经失效

T3  A heartbeat 恢复
    如果只校验 worker_owner，A 可能再次把 lease 延长

T4  Worker B 同时可能竞争 claim
```

这会使“lease 到期即 ownership 失效”的语义出现复活窗口，并削弱 Worker ownership fencing 的时间边界。

## 2. 根因

`_renew_lease_once()` 原逻辑仅使用：

```text
execution.id == execution_id
worker_owner == current_worker
status in {pending, running}
```

缺少：

```text
worker_lease_expires_at > now
```

所以过期 Worker 仍可能凭数据库中残留的 owner 值续租。

## 3. 整改

Heartbeat 续租必须同时满足：

```text
Execution 存在
    AND
worker_owner == current worker
    AND
Execution 未进入终态
    AND
worker_lease_expires_at > now
```

若 lease 已过期，`_renew_lease_once()` 返回 `False`，heartbeat 立即退出；旧 Runtime 后续状态写入继续由既有 ownership fencing 拒绝。

本次整改不改变 Node 状态机，也不允许 `running → running`，不增加第二套 Runtime 或恢复算法。

## 4. 测试要求

必须覆盖：

1. heartbeat 单次数据库瞬态异常后继续下一轮；
2. ownership 失效后 heartbeat 退出；
3. lease 已过期时不能重新续租；
4. Worker recovery 与 ownership fencing 原有测试继续通过。

## 5. 设计结论

Lease 的语义固定为：

> **lease 到期即 ownership 失效；失效 Worker 不允许自行复活 lease。**

Worker 的可靠性依赖顺序保持：

```text
claim
  ↓
lease
  ↓
heartbeat（只能续未过期 lease）
  ↓
ownership fencing
  ↓
Runtime
```

该错误属于 Worker ownership 生命周期边界，不通过延长 timeout、降低 polling 频率或修改状态机解决。
