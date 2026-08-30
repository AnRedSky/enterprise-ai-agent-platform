# 测试误报：Webhook Provider 单元测试依赖真实 DNS 解析

## 1. 现象

Backend 全量测试在约 46% 后出现确定性失败：

```text
tests/unit/test_webhook_delivery_worker.py::test_provider_returns_success_status
WebhookEndpointSecurityError: Webhook endpoint DNS 解析失败
```

测试使用 `https://example.test/hook` 作为 HTTPX MockTransport 的虚拟 endpoint，但生产 Provider 会在发起请求前执行 SSRF/出口安全策略。默认策略要求 hostname 解析成功，并拒绝内部、保留和未解析地址，因此 MockTransport 并不会绕过 endpoint policy。

## 2. 根因

这是测试隔离边界错误，不是 Webhook SSRF 校验缺陷。

生产 Provider 的职责顺序是：

```text
destination.url
    ↓
WebhookEndpointPolicy.validate()
    ↓
SecretResolver.resolve()
    ↓
HTTP client
```

原测试只替换了 `httpx.AsyncClient`，却没有隔离 endpoint policy 和 Secret resolver。结果是：

1. MockTransport 本来可以完全离线处理 HTTP 请求；
2. 但请求前的安全校验仍然执行真实 DNS；
3. `example.test` 在本地环境无法解析；
4. 单元测试因此依赖开发机 DNS 状态而失败。

同时，原测试上下文没有显式提供 `secret_ref`，在修复 DNS 问题后还会继续触发 Secret 配置异常。这说明 fixture 没有完整表达 Provider Contract。

## 3. 修复

不修改生产安全策略，不允许为了通过单元测试而放宽 SSRF 防护。

测试改为显式注入：

- `WebhookEndpointPolicy(allowed_hosts={"example.test"})`：只允许本测试虚拟 hostname，避免真实 DNS；
- `MappingSecretResolver({"test-secret": "unit-test-secret"})`：提供确定性的测试 Secret；
- `httpx.AsyncClient(MockTransport(...))`：通过 Provider 构造函数注入 HTTP client，不再 monkeypatch 全局 `httpx.AsyncClient`。

这样单元测试只验证 Provider 的 HTTP 请求、Header、HMAC 签名及非 2xx 错误映射，不依赖真实网络、DNS 或环境变量。

## 4. 保留的安全边界

生产默认 `WebhookEndpointPolicy` 不变：

- 默认只允许 HTTPS；
- 非 allowlist hostname 必须完成 DNS 解析；
- loopback、private、link-local、multicast、unspecified、reserved 地址继续拒绝；
- 不通过修改测试 fixture 弱化生产 SSRF 防护。

真实 endpoint 的 DNS/网络连通性属于 Real API / integration 层职责，不属于离线 unit test。

## 5. 验证顺序

```powershell
cd backend
uv run pytest -q tests/unit/test_webhook_delivery_worker.py --maxfail=1 -x --tb=long
uv run pytest -q --maxfail=1 -x --tb=long
uv run pytest -q
```

如果新的首个失败出现在其他模块，应继续按“最小复现 → 根因分析 → targeted verification → 全量回归”的顺序处理，不得修改安全策略或扩大单元测试网络权限来规避失败。
