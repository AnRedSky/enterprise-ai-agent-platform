# Real API Test Gate

唯一入口：`01_run_real_api_tests.ps1`。

前置条件由 `00_bootstrap_real_api.py` 自动通过真实 HTTP 注册/登录并准备 Workflow/Execution，禁止手工设置 Token/ID。

当前 Real API Gate 覆盖：

- 基础 Workflow / Version / Execution / Trace / Audit HTTP 验收。
- Node Retry / Attempt。
- Retry Budget Exhausted。
- Workflow Deadline 与 Retry Delay 边界。
- Circuit Breaker：transient failure → OPEN、OPEN Fast-Fail、HALF_OPEN recovery、成功探活后 CLOSED。

Real API Fixture 使用 deterministic Mock Provider，测试不会依赖外部真实模型 Provider。测试结束后 `.real_api_context.json` 与相关环境变量必须清理。

Real API Gate 是 Release / Full Regression Gate 的强制前置质量门；不得由其他测试脚本复制其 Bootstrap/Fixture 逻辑。
