# 2026-08-25 Browser E2E：Trigger 持久化 Config 断言落后于正式 Contract

## 1. 现象

开发者在远端 `main` 基线 `316387d` 执行 Workflow Trigger Browser E2E 时，真实浏览器已经完成 Scheduled Trigger 创建，Scheduler UI 的异步初始化竞争也已经处理完成；测试最终在真实 HTTP 查询持久化 Trigger 时失败：

```text
expect(received).toEqual(expected) // deep equality

Expected:
{ timezone: "UTC", interval_seconds: 60 }

Received:
{
  timezone: "UTC",
  interval_seconds: 60,
  misfire_policy: "skip",
  catch_up_limit: 10,
}
```

## 2. 根因

该失败属于 E2E 测试断言与正式 Scheduler Trigger Contract 漂移，而不是生产代码返回了错误数据。

Phase 2.4 已明确 Scheduled Trigger 配置允许持久化：

```text
misfire_policy: skip | fire_once | catch_up
catch_up_limit: 1..100，默认 10
```

当前 Backend 在创建 Scheduled Trigger 时对未显式提交的 misfire 配置补齐正式默认值，因此真实 PostgreSQL 持久化实体包含四个字段：

```json
{
  "timezone": "UTC",
  "interval_seconds": 60,
  "misfire_policy": "skip",
  "catch_up_limit": 10
}
```

此前 E2E 只断言早期的 `timezone + interval_seconds` 子集，并在最终持久化检查中使用 `toEqual` 强制要求旧的两字段对象，导致测试错误地把合法的 Backend 默认值识别为失败。

## 3. 修复边界

本轮只修复 Browser E2E 对正式持久化 Contract 的断言，不修改 Scheduler Runtime、Repository、misfire 算法或生产 API。

调整为：

1. Trigger 首次持久化查询同时验证 `timezone / interval_seconds / misfire_policy / catch_up_limit`；
2. 最终 PostgreSQL 持久化实体使用完整正式 Config 做 `toEqual`；
3. Scheduler API 与 UI 原有 `skip / 10` 断言保持不变；
4. 不降低断言强度，不使用固定 sleep，不构造测试数据。

## 4. 验证要求

必须由开发者在本地重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

只有出现 Playwright `1 passed` 且脚本最终输出 `[PASS]`，才能将 Workflow Trigger Browser Gate 标记为通过。

随后继续执行 `docs/PROJECT_STATUS.md` 规定的 Frontend Regression、Backend Regression、Tenant Safe Real API 与 Phase 2.4 Acceptance 汇总。
