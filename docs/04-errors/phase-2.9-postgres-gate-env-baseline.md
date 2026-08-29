# Phase 2.9 PostgreSQL Gate：环境配置基线检查错误

## 1. 问题

Phase 2.9-C PostgreSQL Real Gate 在执行前检查 `backend/.env` 或 `backend/.env.dev` 是否存在。当前项目已经将 `backend/.env.example` 纳入 `Settings` 的默认环境配置加载链，因此该检查与实际配置机制不一致。

在只保留统一 `backend/.env.example` 的本地环境中，Gate 会在任何 Alembic 或 pytest 执行之前错误终止：

```text
No backend/.env or backend/.env.dev was found; PostgreSQL connection configuration cannot be verified.
```

## 2. 根因

测试 Gate 沿用了旧的多环境文件存在性假设，而配置实现已经把 `.env.example` 作为默认本地配置基线。Gate 的前置校验没有与 `app/core/config.py` 的配置加载策略同步。

## 3. 修复

`backend/scripts/test/phase-2.9/01_reliable_delivery_postgres_gate.ps1` 改为：

1. 只校验 `backend/.env.example` 是否存在。
2. 不要求开发者创建、复制或手工填写 `.env` / `.env.dev`。
3. 明确输出统一配置基线为 `backend/.env.example`。
4. 保持 Gate 不启动、不停止 API、Worker、Scheduler、Redis、PostgreSQL 的既有服务策略。

## 4. 验证要求

修复后必须在本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\01_reliable_delivery_postgres_gate.ps1
```

实际通过、失败及环境阻塞状态必须以本地执行结果为准，不得预填验收结论。
