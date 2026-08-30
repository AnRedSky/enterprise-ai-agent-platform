# 本地回归脚本路径解析修复

## 问题

`frontend/scripts/test/run-local-full-regression.ps1` 原先将 `$PSScriptRoot\..\..\..` 解析为项目根目录，却随后在该目录检查 `package.json`，导致从 `frontend` 目录执行 `npm run test:local:full` 时错误提示 `frontend/package.json not found.`。

## 修复

脚本实际位于 `frontend/scripts/test`，因此 `$PSScriptRoot\..\..` 才是 `frontend` 根目录。脚本现在基于 `$PSScriptRoot` 解析 `frontendRoot`，完全不依赖调用者当前工作目录。

支持以下等价调用方式：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:local:full
```

或：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform
powershell -NoProfile -ExecutionPolicy Bypass -File .\frontend\scripts\test\run-local-full-regression.ps1
```

## 服务生命周期边界

脚本只执行依赖预检、Vitest、Build、Regression Gate 与已有服务 readiness 检查；不会自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，也不会要求手工输入测试数据。缺少 E2E 所需服务时保持 `NOT EXECUTED`，由本地标准运行手册负责服务生命周期。

## 验证要求

依赖恢复后执行：

```powershell
npm ci
npm run test:local:full
```

在本地实际输出产生前，不将 Full Regression 标记为通过。
