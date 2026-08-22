# 2026-08-22 — E-2 governed evaluation placeholder command

## 现象

E-2 手动验证命令使用了字面量 `<PROFILE_A_UUID>` / `<EMBEDDING_PROFILE_UUID>` 作为示例占位符，并直接在 PowerShell 中执行。PowerShell 将 `<` 解释为保留的重定向语法，因此命令在进入 Python runner 前即产生 `RedirectionNotSupported` / `ParserError`。

## 原因

示例命令中的占位符没有明确要求先替换成数据库中真实存在、且当前 actor 可访问的 Embedding Model Profile UUID。

## 修正

- 文档中的命令继续使用 `<...>` 仅作为说明性占位符，不应直接复制执行。
- 新增 `backend/scripts/evaluation/knowledge/run_governed_embedding_profile_smoke.py`，自动从本地 PostgreSQL 选择 active Organization/member，创建临时 governed Ollama Provider 与两个 Embedding Profile，并使用本地已安装模型完成 A/B baseline identity 验证。
- Smoke script 在执行前通过 Ollama `/api/tags` 检查模型存在，并通过 `/api/embed` 获取实际 dimension；不会执行模型下载。
- 测试结束后删除临时 Provider/Profile，避免污染正式治理数据。

## 本地执行要求

当前开发环境必须已经存在两个可用的 Embedding 模型。默认使用：

- `nomic-embed-text:latest`
- `bge-m3:latest`

如本地模型名称不同，可通过 `--profile-a-model` / `--profile-b-model` 指定；脚本不会自动下载任何模型。

## 状态

代码修正已提交；Real Provider smoke 的实际通过结果必须由开发者在本地执行后再记录到 Project Status / Acceptance，不在提交前预填 Passed。
