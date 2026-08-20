# Frontend / Backend Integration Test Layer

本目录不再提供重复的“全套质量门编排”脚本。

## 职责

- `backend/tests/integration/`：Backend 内部多 Service / Repository / 基础设施真实组合行为。
- `backend/tests/api_real/`：真实 HTTP API 验收。
- `backend/scripts/test/api-real/`：Real API Gate 与 Fixture 编排。
- `backend/scripts/test/release/`：Release / Full Regression Gate，负责按固定顺序编排 Backend regression、Migration、Real API、Frontend test/build。
- `backend/scripts/test/integration/`：仅保留未来真正的 Frontend / Backend E2E 或联调编排入口；不得复制 Unit、Integration、Real API 或 Frontend regression 的已有测试。

当前尚未实现浏览器级 E2E，因此本目录不提供 `01_frontend_backend_gate.ps1`。真正的 Browser E2E 应在独立测试实现和明确浏览器测试工具确定后再增加。

## Full Regression Gate

从 `backend` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_full_regression_gate.ps1
```

该 Gate 不等同于 Browser E2E，也不替代 `tests/integration`、`tests/api_real` 或 `scripts/test/api-real`。
