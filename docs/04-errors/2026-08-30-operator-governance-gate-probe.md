# 2026-08-30 Operator Governance Gate 探测脚本修正

## 现象

Real Gate 初版的 PowerShell Python 单行探测把 `async def` 放入分号语句序列，Python 语法不允许这种 compound statement 组合方式。

## 根因

异步数据库探测被错误压缩成单行 Python 语句，没有遵守 Python compound statement 的语法边界。

## 修复

改用项目已有的 `uv run alembic current` 作为 PostgreSQL 可用性探测，不再在 Gate 内拼接异步 Python 代码。

## 防回归

后续 Gate 优先复用 Alembic 或已有项目健康检查入口；需要异步 Python 探测时使用独立脚本文件。
