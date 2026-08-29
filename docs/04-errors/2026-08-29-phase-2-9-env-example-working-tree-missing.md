# Phase 2.9：`.env.example` 本地工作区缺失导致 Real Gate 前置检查失败

## 1. 现象

Phase 2.9-C PostgreSQL Real Gate 在 `[0/3] Local prerequisite verification` 阶段停止，并提示 `backend/.env.example was not found`。

开发者本地执行时使用的是项目 `main` 分支工作区；远端 `main` 实际已包含受版本控制的 `backend/.env.example`，因此该失败不是 PostgreSQL 连接失败，也不是业务代码失败，而是本地工作区缺少已跟踪的统一配置基线文件。

## 2. 根因

Gate 原实现只检查文件系统中的 `backend/.env.example`：

```powershell
Test-Path $envExampleFile
```

当该文件因本地工作区状态异常而缺失时，脚本直接失败，没有利用 Git 中当前 `HEAD` 已跟踪的同名文件进行恢复。

## 3. 修复

Phase 2.9-C Gate 现在采用以下顺序：

1. 检查 `backend/.env.example` 是否存在；
2. 若不存在，使用 `git ls-files --error-unmatch .env.example` 确认当前 `HEAD` 确实跟踪该文件；
3. 确认后执行 `git restore --source=HEAD -- .env.example` 自动恢复；
4. 恢复失败或当前 `HEAD` 未跟踪该文件时才终止 Gate。

该修复不会要求开发者创建、复制或手工填写 `.env` / `.env.dev`，也不会启动或停止任何服务。

## 4. 边界

- `.env.example` 仍然是 Phase 2.9 Real Gate 的统一本地配置基线；
- 真实 Secret 不写入仓库；
- Gate 不自动启动 API、Worker、Scheduler、Redis 或 PostgreSQL；
- 测试数据仍由测试自动生成；
- 如果当前 `main` 本身没有跟踪 `.env.example`，Gate 会明确要求先同步 `main`，而不是生成未经版本控制的配置文件。

## 5. 验证

代码修复提交后，由开发者在最新 `main` 工作区重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\01_reliable_delivery_postgres_gate.ps1
```

Real Gate 的 PostgreSQL、Migration 与业务测试结果必须以本地实际执行结果为准，不预填通过状态。
