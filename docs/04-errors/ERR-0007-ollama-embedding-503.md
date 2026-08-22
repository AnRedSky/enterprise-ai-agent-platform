# ERR-0007 — 本地 Ollama Embedding 503 / Runner 启动与环境代理

## 现象

2026-08-22 开发者在本地执行真实 Ollama embedding smoke 时，`POST http://localhost:11434/api/embed` 曾返回 HTTP 503。随后直接在 Ollama 容器内执行同一模型可以正常生成 768 维向量；Ollama 日志在部分失败时段没有对应的 `/api/embed` 请求记录。

修复后再次执行：

```text
provider = ollama
model = nomic-embed-text:latest
expected_dimension = 768
vector_count = 1
actual_dimension = 768
provider_dimension = 768
status = PASS
```

并在真实 Retrieval evaluation 中确认：

```text
cases=5
successful_cases=5
error_rate=0
fallback_count=0
fallback_used=false
```

## 根因分析

问题并非 embedding 模型本身不可用。Ollama 容器日志显示模型 runner 能够加载 `nomic-embed-text-v1.5` 并最终返回 200；部分 503 与 runner 尚未准备完成以及本机环境代理有关。

本地 endpoint 继承机器级 HTTP(S) proxy 时，请求可能在到达 Docker Ollama 之前被代理层处理并返回合成 503，因此 Ollama 容器没有对应请求日志。另一个真实场景是首次加载 runner 需要等待模型启动，过早请求会得到暂时不可用状态。

## 修复

1. Ollama embedding provider 对 `localhost`、`127.0.0.1`、`::1` endpoint 禁用环境代理继承，远程 Ollama endpoint 保持原有 proxy 行为。
2. 对 transient native Ollama runner startup / 503 增加受控 retry，等待 runner ready，而不是立即把暂时性启动失败判定为永久 provider unavailable。
3. 保留 dimension contract；实际向量维度不匹配仍 fail loud，不允许截断、补零或伪造 baseline。

对应代码提交：

- `7da7ced` — `fix: tolerate slow native Ollama runner startup`
- `2c2d94b` — `fix: bypass environment proxy for local Ollama`

## 验证

开发者本地已执行：

```text
uv run pytest -q tests/unit/test_ollama_embedding_provider.py
11 passed

uv run pytest -q
301 passed, 30 deselected

uv run python .\scripts\test_ollama_embedding.py
status = PASS

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
Backend regression: 301 passed, 30 deselected
Real HTTP API: 30 passed
```

Ollama 日志最终确认 `/api/embed` 返回 HTTP 200。

## 边界

该错误只记录本次已分析并修复的本地工程问题。Real Provider 的模型质量不因该错误修复而自动变为绝对质量达标；真实 Retrieval baseline 仍必须单独记录和回归比较。
