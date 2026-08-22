# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已通过本地 Gate。
- 2.2-C Real Provider Quality Gate：已实现，当前受本地 embedding 模型维度阻塞。

## 本轮实际验证

```text
Ollama /api/tags: 3 models available
Model Gateway unit: 5 passed
Backend regression: 287 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
```

当前 Ollama embedding 模型为 `nomic-embed-text`（768 维）和 `bge-m3`（1024 维），而 pgvector 契约为 `vector(1536)`；当前资源约束禁止下载其他模型，因此不得绕过维度校验或伪造 baseline。

已新增 `backend/scripts/dev/ollama_chat_smoke.ps1` 解决 PowerShell 手工 JSON quoting 问题，并记录到 `docs/04-errors/`。

正确 Frontend Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

## 下一步

1. 执行 Ollama Chat smoke test。
2. 保持 Backend / Frontend / Browser Gate 独立。
3. 不下载其他模型、不伪造 embedding baseline。
4. 获得可实际产生 1536 维 embedding 的 Provider，或明确批准调整 pgvector 维度后，执行 2.2-C `--freeze-baseline`。
5. 冻结真实 baseline 后进入 2.2-D Retrieval Quality Regression。
