# Backend 测试目录规范

## 目录职责

- `tests/`：单元测试、Service/Model/Schema 等内部行为测试，以及尚未迁移的历史测试。
- `tests/api_contract/`：API Contract 测试。测试路由注册、认证边界和接口 Contract，可使用 TestClient / ASGITransport。
- `tests/api_real/`：真实 HTTP API 测试。必须连接独立运行的 Backend 服务，通过 `httpx` 发起实际 HTTP 请求。

## API 测试执行顺序

真实 API 测试必须在前后端联调之前完成：

```powershell
$env:ACCESS_TOKEN="<real bearer token>"
$env:WORKFLOW_ID="<workflow id>"
$env:WORKFLOW_EXECUTION_ID="<execution id>"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_real_validation.ps1
```

未通过真实 API gate 时，禁止进入浏览器前后端联调。

## 单元 / Contract 与 Real API 的区别

`pytest -q` 不等价于 Real API 验收。前者验证本地代码行为；后者验证实际启动服务的 HTTP Contract、认证、租户数据访问和治理查询。
