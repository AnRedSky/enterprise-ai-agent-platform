# 2026-09-02 Scheduler misfire `catch_up_limit=0` 未触发参数校验

## 1. 现象

开发者执行 Scheduler Misfire / Lease Gate 时，PostgreSQL readiness 已通过，但 misfire unit regression 出现：

```text
FAILED tests/unit/services/workflow_scheduler/test_misfire.py::test_catch_up_requires_positive_limit
Failed: DID NOT RAISE <class 'ValueError'>
1 failed, 4 passed in 0.66s
```

## 2. 根因

`choose_misfire_slots()` 原实现先判断：

```python
if not ordered or policy is MisfirePolicy.SKIP:
    return ()
```

然后才校验 `catch_up_limit`。因此当 `missed_slots` 为空时，即使调用方显式传入 `catch_up_limit=0`，函数也提前返回，不会执行参数边界校验。

该行为使“配置参数非法”与“本轮没有待处理槽位”产生错误的短路关系：调用契约要求 `catch_up_limit` 始终为正数，而参数校验不应依赖当前是否存在待处理槽位。

## 3. 修复

将 `catch_up_limit` 校验移动到任何提前返回之前，并拒绝 `bool` 作为整数配置：

```python
if isinstance(catch_up_limit, bool) or catch_up_limit < 1:
    raise ValueError("catch_up_limit 必须大于等于 1")
```

这样 `catch_up_limit` 的非法值在所有 misfire policy 与槽位数量下都具有一致语义，同时保持 `skip` 不处理槽位的业务规则不变。

## 4. 测试边界

现有单元测试继续覆盖：

- `skip` 丢弃历史积压；
- `fire_once` 只选择最早槽位；
- `catch_up` 遵守正数上限；
- `catch_up_limit=0` 必须抛出 `ValueError`；
- 长时间积压的槽位生成受 `limit` 有界约束。

后续应在开发者本地重新执行 Scheduler Misfire / Lease Gate，并以实际输出作为验收依据。
