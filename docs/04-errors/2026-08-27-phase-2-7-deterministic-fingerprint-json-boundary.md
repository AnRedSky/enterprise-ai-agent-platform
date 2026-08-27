# Phase 2.7：Deterministic Decision Fingerprint JSON Boundary

- 日期：2026-08-27
- 阶段：Phase 2.7-A Closure Invariant Sweep
- 类型：Recovery / Planner 一致性

## 问题

`WorkflowDagResumePlanner` 原先使用 `json.dumps(..., default=str)` 生成 `decision_fingerprint`。这会把非 JSON-safe 的条件 state 隐式转换成字符串，可能让同一业务事实在不同 Python 对象表示下产生可接受但不严格的 Decision identity。

同时 `json.dumps` 默认允许 `NaN` / `Infinity` 等非标准 JSON 数值，导致 fingerprint 输入边界与持久化 JSON 数据边界不一致。

## 修复

Planner 的 fingerprint canonicalization 现在：

1. 移除 `default=str`，不再静默转换非 JSON 类型；
2. 使用 `allow_nan=False`；
3. 对无法 canonicalize 的 condition state 立即抛出 `ValueError`；
4. 保持 `sort_keys=True`、固定 separators、UTF-8，继续保证确定性 hash。

## 不变量

```text
Durable condition state
        ↓
JSON-safe canonical representation
        ↓
SHA-256 decision fingerprint
```

无法形成合法 canonical representation 时必须拒绝 Recovery Decision，而不是猜测转换。

## 测试

Unit Test 增加非 JSON-safe / NaN condition state 场景。完整 Regression、E2E、Real API 暂不作为主线阻塞条件。
