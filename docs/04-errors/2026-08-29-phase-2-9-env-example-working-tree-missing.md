# Phase 2.9：`.env.example` 本地工作区缺失与 Gate 路径解析错误

## 1. 现象

Phase 2.9-C PostgreSQL Real Gate 在 `[0/3] Local prerequisite verification` 阶段停止。开发者本地 `backend/.env.example` 已存在，但 Gate 仍执行了 Git 基线检查并报告 `.env.example` 不受当前 checkout 跟踪。

## 2. 根因

Gate 原实现使用 `$PSScriptRoot` 向上四级计算 `$BackendRoot`。脚本实际位于 `backend/scripts/test/phase-2.9`，向上四级得到的是仓库根目录，而不是 `backend` 根目录。

因此脚本实际检查的是仓库根目录的 `.env.example`，而项目统一配置文件位于 `backend/.env.example`。随后执行 `git ls-files --error-unmatch -- .env.example` 时同样检查了错误的 Git 路径，于是即使 `backend/.env.example` 已存在，也会错误失败。

## 3. 修复

1. 将 `$BackendRoot` 的路径计算从向上四级修正为向上三级；
2. Gate 进入后始终切换到真实 `backend` 根目录；
3. 环境文件路径固定解析为 `backend/.env.example`；
4. 文件缺失时使用 `git cat-file -e HEAD:backend/.env.example` 检查当前提交树，而不是依赖本地 Git index；
5. 确认当前 `main` 提交包含该文件后，再执行 `git restore --source=HEAD -- .env.example` 自动恢复工作区；
6. Gate 仍不创建、复制或要求开发者手工填写 `.env` / `.env.dev`，也不启动或停止任何服务。

## 4. 边界

- `backend/.env.example` 是 Phase 2.9 Real Gate 的统一无 Secret 配置基线；
- `.env.example` 不包含真实凭据；
- Real Gate 不自动启动或停止 API、Worker、Scheduler、Redis 或 PostgreSQL；
- 测试数据由测试自动生成；
- 当前 `main` 提交本身不包含 `backend/.env.example` 时，Gate 必须明确失败并要求同步正确的 `main`，不得生成未受版本控制的替代配置。

## 5. 验证

修复提交后，在 `backend` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\01_reliable_delivery_postgres_gate.ps1
```

本轮代码修复后的 PostgreSQL、Migration、Real API 与 Unit 测试结果必须以开发者实际执行输出为准，不预填通过状态。
