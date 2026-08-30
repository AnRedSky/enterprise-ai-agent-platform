# ERR-0033 Global Runtime Operations Agent Filter SQL Contract 漂移

## 现象

Phase 2.10-II Global Runtime Operations Unit / Real Gate 均在 `test_global_runtime_agent_filter_uses_workflow_version_definition` 处失败。

失败断言要求 `_agent_filter(agent_id)` 编译后的 PostgreSQL 表达式包含 `workflow_version_id` 与 `agent_id`，但实际 SQL 为对 `workflow_versions.definition` 使用 `->>` JSON 操作符，并把 JSON key `agent_id` 作为 SQLAlchemy 绑定参数处理，因此编译文本中不存在 `agent_id` 字面量。

## 根因

`WorkflowVersion.definition` 是 JSON 字段，原实现使用：

```python
WorkflowVersion.definition["agent_id"].as_string()
```

该写法在 PostgreSQL 编译阶段会将 JSON key 参数化。业务语义本身没有丢失，但 Global Runtime Operations 的 SQL Contract 测试同时把固定协议字段名 `agent_id` 作为可观测 SQL 结构的一部分进行验证，导致生产实现与既有 Contract 不一致。

该问题不是缺少 Agent 生命周期实现。平台约定 Agent 关联事实继续来自 `WorkflowVersion.definition.agent_id`，不得新增第二套 Agent 生命周期或独立运行时事实源。

## 修复

将固定的 JSON 协议字段名改为 SQLAlchemy `literal_column("'agent_id'")`，通过 PostgreSQL `->>` 运算符读取：

```python
WorkflowVersion.definition.op("->>")(literal_column("'agent_id'")) == str(agent_id)
```

这样：

1. `agent_id` 作为固定协议字段名出现在编译 SQL 中；
2. 外部传入的 UUID 仍通过 SQLAlchemy 绑定参数传递，不拼接用户输入；
3. 查询仍通过 `workflow_version_id` 关联 Execution，继续复用现有 Workflow / WorkflowVersion 生命周期；
4. 不引入新的 Agent Service、Repository 或生命周期实现。

## 预防

- JSON definition 中作为稳定 Contract 的固定字段应在 SQL 编译层保持可识别的协议结构。
- 测试既要验证查询语义，也要验证必要的 SQL Contract；生产代码不得为了通过测试复制第二套业务规则。
- 新增运行时关联过滤器前必须先检索现有 Workflow / WorkflowVersion / Execution 正式入口。

## 验证边界

本次修复目标是消除 Global Runtime Operations Agent Filter 的编译 Contract 漂移。代码提交后必须由开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_global_runtime_operations.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\06_global_runtime_operations_unit_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\07_global_runtime_operations_real_gate.ps1
uv run pytest -q
```

上述命令在代码修复完成时不预填“通过”；最终状态以实际本地执行结果为准。
