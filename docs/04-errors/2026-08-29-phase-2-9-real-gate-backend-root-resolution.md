# 2026-08-29 Phase 2.9 Real Gate Backend Root Resolution

## 1. 现象
本地执行 `backend/scripts/test/phase-2.9/03_runtime_integration_real_gate.ps1` 时，工作区存在 `backend/.env.example`，但 Gate 报告：

> backend/.env.example is required as the unified test configuration baseline.

## 2. 根因
`03_runtime_integration_real_gate.ps1` 与 `02_webhook_delivery_real_gate.ps1` 均从脚本目录 `backend/scripts/test/phase-2.9` 向上解析 Backend Root。

正确路径层级为：

`phase-2.9 -> test -> scripts -> backend`

因此只需要三级 `..\..\..`。原实现使用四级 `..\..\..\..`，实际解析到了仓库根目录，随后在错误目录检查 `.env.example`，导致即使 `backend/.env.example` 存在也被判定为缺失。

## 3. 修复
统一修改两个 Real Gate：

```powershell
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
```

Gate 继续以 `backend/.env.example` 作为统一本地测试配置基线，不读取或要求提交 `.env` / `.env.dev`。

## 4. 影响范围
- Phase 2.9-E Runtime Integration Real Gate
- Phase 2.9-D Webhook Delivery Real Gate
- 不涉及生产运行时业务逻辑。

## 5. 验证要求
修复后应在 `backend` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\03_runtime_integration_real_gate.ps1
```

若本地基础服务已按项目要求运行，Gate 应先通过 `.env.example` 前置检查，再进入 Alembic、Runtime Integration Real Acceptance、targeted regression 和 Webhook Real Acceptance。

## 6. 服务策略
该 Gate 不启动、不停止 API、Worker、Scheduler、Redis 或 PostgreSQL；测试数据由验收测试自动生成，不要求手工填写测试数据。
