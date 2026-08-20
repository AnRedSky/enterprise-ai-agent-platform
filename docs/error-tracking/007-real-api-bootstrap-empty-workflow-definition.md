# 007 Real API bootstrap 选择了不可执行的已发布 Workflow

## 发生阶段

Phase 1.5-F / Real API Gate。

## 发生命令

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

## 错误摘要

Real API bootstrap 在创建执行时返回 HTTP 422：

```text
POST /workflows/{workflow_id}/executions -> 422
Workflow definition 必须包含非空 nodes
```

此前 bootstrap 在没有可用发布 Workflow 时创建了空 definition：

```json
{"nodes": [], "edges": []}
```

同时，bootstrap 会优先复用任意带 `published_version_id` 的 Workflow；如果该已发布版本的 definition 为空，也会被错误地选为 Real API 执行 fixture。

## 根因

Workflow Runtime 当前要求 Workflow definition 至少包含一个非空 `nodes` 集合；`input` / `output` 是当前 Runtime 支持的基础节点类型。Real API bootstrap 的测试 fixture 与这一运行时契约不一致，并且缺少对已发布版本 definition 的可执行性检查。

## 修复方案

1. 将 bootstrap 创建的 fixture 改为最小可执行定义：`input -> output` 节点集合。
2. 复用已有 Workflow 前先读取其已发布 Version definition。
3. 只有已发布 definition 包含非空 `nodes` 时才复用该 Workflow。
4. 没有可执行已发布 Workflow 时自动创建新的有效 fixture。
5. 保持 Real API 的 token / Workflow ID / Execution ID 自动生成机制，不要求开发人员手工填写。

## 验证结果

代码修复已提交到 `main`，commit：`2aab1dc8f619e604d76a7d97845e7669857f147c`。

开发者本地仍需重新执行 Real API Gate，确认 bootstrap、Workflow Execution、Audit 与 Trace 全链路通过。

## 防重复措施

Real API bootstrap 必须保证测试执行 fixture 满足当前 Workflow Runtime definition contract；不得使用空 `nodes` 的已发布版本作为执行测试上下文。
