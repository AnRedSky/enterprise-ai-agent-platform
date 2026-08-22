# 本地开发与配置基线

## 1. 目标

开发、启动服务和本地测试默认直接读取 `backend/.env.example`，新 checkout 不要求先复制或修改配置文件。

`backend/.env.example` 是无 Secret 的、可执行的本地开发基线：

- Chat：优先使用 Docker 发布到宿主机 `localhost:11434` 的 Ollama。
- 当前本地 Chat 模型：`qwen3:0.6b`。
- Ollama 不可达、模型不存在或请求失败时，Model Gateway 在 `MODEL_FALLBACK_TO_MOCK=true` 下自动退回确定性的 MockProvider。
- Retrieval Embedding 默认保持 Mock，因为当前数据库 pgvector 契约为 1536 维，而现有本地 Ollama embedding 模型维度不一致；不得为了启动方便进行截断、补零或隐式改维度。
- PostgreSQL / Redis 默认使用项目本地服务地址。

## 2. 配置优先级

Backend 配置按以下顺序从低到高覆盖：

```text
.env.example
→ .env
→ .env.local
→ .env.${APP_ENV}
→ .env.${APP_ENV}.local
→ ENV_FILE
→ process environment
```

因此，开发者通常不需要创建 `.env`。需要覆盖配置时使用未提交的 `.env.local` 或进程环境变量。

## 3. 启动 Backend

在 `backend` 目录：

```powershell
uv run uvicorn app.main:app --reload
```

默认使用 `.env.example`。只有部署、特殊联调或 Secret 注入场景才需要显式 `ENV_FILE` / `.env.local`。

## 4. 验证 Ollama

宿主机必须能访问 Docker 发布的端口：

```powershell
curl.exe http://localhost:11434/api/tags
```

应至少存在：

```text
qwen3:0.6b
```

Chat OpenAI-compatible endpoint：

```powershell
curl.exe http://localhost:11434/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer ollama" `
  -d '{"model":"qwen3:0.6b","messages":[{"role":"user","content":"本地模型连接测试"}],"stream":false}'
```

不需要下载额外模型。

## 5. Mock fallback 边界

Fallback 只服务于本地开发和调试连续性。它不能被视为真实模型质量结果，也不能用于冻结或证明 Real Provider Quality baseline。

因此：

- 本地 Runtime / UI 调试：允许 Ollama → Mock fallback。
- `tests/unit`：允许显式验证 fallback 行为。
- Phase 2.2-C Real Provider Quality Gate：必须关闭 fallback，并显式记录真实 Provider failure。
- Retrieval Embedding 的 Mock 与 Chat 的 Mock fallback 是两个独立边界，不得混用。

## 6. 推荐测试顺序

```powershell
cd backend
uv run pytest -q tests/unit/test_model_gateway.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

前端保持独立执行自己的 regression gate。Browser E2E 也保持独立，不由 Backend 配置脚本隐式编排。

## 7. Secret 规则

`backend/.env.example` 可以提交，但只能包含本地服务地址、兼容占位值和安全默认值。真实 API key、Token、密码和生产 endpoint 必须进入未提交配置或部署 Secret。
