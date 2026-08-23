# 2026-08-23 Phase 2.3 Real API Provider Timeout Fallback Reason Contract

## 现象

在开发者本地执行 Tenant Safe Real API Gate 时，Phase 2.3 runtime governance 场景 `test_runtime_uses_published_model_profile_and_records_usage_identity_without_mock_fallback` 已完成 Runtime 执行并落库 trace，但测试断言失败：

```text
assert identity["fallback_reason"] == "connectivity"
AssertionError: assert 'timeout' == 'connectivity'
```

同一轮 Gate 其余 33 个 Real API 测试通过，失败为测试契约断言与当前 Runtime provider timeout 语义不一致，并非 trace response shape 或 Provider/Profile governance lookup 失败。

## 根因

该场景创建的 fixture Provider endpoint 为 `http://127.0.0.1:1/v1`，同时 Profile 明确设置 `timeout_seconds=0.25`。当前真实 HTTP Provider 调用路径将该失败归类为 `timeout`，与 Phase 2.3-A 定义的 fallback eligibility reason 一致。

测试仍断言旧的 `connectivity` reason，因此出现 false negative。

## 修复

提交 `43f9e683d00d936db94f249b4e587654e9517914` `test(real-api): align provider timeout fallback reason` 已将该 Real API 断言从 `connectivity` 调整为 `timeout`。

本修复不改变 Runtime 行为，不改变数据库 schema，也不引入 Mock fallback；仅使 Real API 测试契约与实际 timeout 分类保持一致。

## 验证状态

开发者已反馈的失败结果：

```text
Real API Gate: 33 passed, 1 failed
Failure: fallback_reason expected connectivity, actual timeout
```

修复提交后尚未由开发者重新执行完整 Tenant Safe Real API Gate，因此不得记录为 Passed。

## 后续动作

1. 拉取远端 `main` 至包含 `43f9e683` 的最新提交。
2. 重新执行 Tenant Safe Real API Gate。
3. 若通过，再执行 Backend default regression、Migration/head verification 与 Real API 三层 Backend Gate。
4. 若出现新的实际失败，继续新增对应 `docs/04-errors/` 记录并按开发准则直接修复 `main`。
