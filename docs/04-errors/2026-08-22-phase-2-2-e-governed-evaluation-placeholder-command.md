# 2026-08-22 — E-2 governed evaluation placeholder command / async fixture lifecycle

## 现象

E-2 手动验证命令曾使用字面量 `<PROFILE_A_UUID>` / `<EMBEDDING_PROFILE_UUID>` 作为示例占位符并直接在 PowerShell 执行，导致 `RedirectionNotSupported` / `ParserError`，命令未进入 Python runner。

在 governed smoke 的早期实现中，数据库 fixture 创建/清理与 runner 又跨越多个 `asyncio.run()` event loop，存在异步数据库资源跨 event loop 生命周期不安全的问题。

## 原因

- PowerShell 示例没有足够明确地要求先替换真实 UUID。
- Smoke script 将 async DB fixture lifecycle 拆到多个 event loop，而 SQLAlchemy async engine/session 资源应保持在同一生命周期内。

## 修正

- 文档中的 `<...>` 只作为说明性占位符，不应直接复制执行；优先使用自动化 smoke script。
- `run_governed_embedding_profile_smoke.py` 改为单一 async event loop：fixture 创建、runner 前后 cleanup 均在同一 loop 内完成。
- Smoke script 仍只检查本地已安装模型，不执行 `ollama pull`。
- 测试结束后删除临时 Provider/Profile 并清理 Evaluation Vector Space，避免污染正式治理数据。

## 实际验证

2026-08-23 开发者实际执行 governed smoke：`status=passed`；Profile A=`nomic-embed-text:latest` / 768，Profile B=`qwen3-embedding:0.6b` / 1024。Profile B 因 model / dimension / model_profile_id identity 改变触发预期 regression，顶层 smoke 仍为 passed。

## 状态

代码修正已在 main 提交；本次本地验证结果已同步到 `PROJECT_STATUS.md`、Phase 与 Acceptance。后续验证继续以开发者本地实际执行为准。