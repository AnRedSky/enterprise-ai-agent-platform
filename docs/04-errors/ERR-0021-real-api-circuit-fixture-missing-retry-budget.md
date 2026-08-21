# ERR-0021 — Real API Circuit Breaker fixture 未配置 workflow retry budget

## 状态

**Resolved in test fixture — 等待开发者本地 Real API Gate 验证。**

## 发现阶段

Phase 1.9-C Real API Reliability Scenarios。

## 现象

Real API bootstrap 的 Circuit Breaker Open fixture 预期通过第二次 node call 触发已经打开的 Circuit Breaker，最终得到 `HTTP 503 / CIRCUIT_OPEN`。

实际第一次 `mock-http-503` 调用失败后，Workflow Runtime 因默认 `retry_budget.max_retries = 0` 直接耗尽 workflow retry budget，因此没有进入第二次 Runtime call。Execution 持久化为：

```text
status=failed
error_code=HTTP_503
```

bootstrap 因而认为 fixture 状态错误。

## 根因

Circuit Breaker 的 node retry policy 配置了 `max_attempts=2`，但 workflow 级 retry budget 未配置。当前 Runtime 将 workflow retry budget 默认解释为 `max_retries=0`，因此 node retry 不能仅靠 node-level `max_attempts` 穿透 workflow budget。

## 修复

Real API Circuit Breaker Open fixture 的 workflow definition 增加：

```json
{"retry_budget": {"max_retries": 1}}
```

这样第一次 provider 失败后允许一次 workflow-level retry，第二次调用进入已打开的 Circuit Breaker，才能验证 `CIRCUIT_OPEN` boundary。

## 验证要求

必须由开发者本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

不得以 bootstrap 单独成功替代完整 Real API Gate 验收。