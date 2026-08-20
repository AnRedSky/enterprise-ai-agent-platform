# Phase 1.5-F：Workflow Runtime Tenant Scope 整改

## 目标

在 Workflow Execution 已形成 `Published Version → Create → Run → Status/Nodes → Audit/Trace` 闭环后，继续补强 Runtime 的多租户边界。

## 整改内容

Workflow 的 `agent` node 在 Runtime 执行时，除了已有的：

- published Agent Version 校验
- 非管理员 owner 权限校验

新增要求：

- 从当前 Workflow Execution 传递 `tenant_id` 到 Runtime。
- Agent 查询通过 `Agent.owner_id → User.tenant_id` 限定到当前 Workflow 所属 tenant。
- 即使调用方具有 admin 角色，也不能通过 Workflow Runtime 跨 tenant 解析并执行 Agent。

这样保证：

```text
Workflow tenant
      ↓
Workflow Execution tenant
      ↓
Workflow Runtime
      ↓
Agent owner tenant
```

四层 scope 保持一致。

## 测试

新增 Runtime unit test，锁定带 tenant scope 时 Agent 查询必须包含 User tenant 条件。

没有新增测试入口，也没有改变既有 `tests / scripts` 职责隔离。

## 验收

```powershell
cd backend
uv run pytest -q
```

同时继续使用既有前端测试与构建入口验证没有回归。

## 边界

本项只做 Runtime tenant isolation，不新增 DAG 编排器，不继续人工拆分 vendor chunk，也不引入新的开发/测试脚本入口。
