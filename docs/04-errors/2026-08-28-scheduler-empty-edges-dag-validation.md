# 2026-08-28 Scheduler 空 edges 被误判为非法 DAG

## 1. 现象

在最新 `main` 基线 `7e8dc07f` 上，Backend Regression 与 Phase 2.8 B2 Worker Execution Bridge Gate 均通过，但独立运行 `uv run python run_scheduler.py` 时持续输出：

```text
fastapi.exceptions.HTTPException: 422: DAG Workflow 必须包含非空 edges
```

调用链为：

```text
ScheduledTriggerScheduler.tick_once
  -> WorkflowTriggerService.invoke_scheduled
  -> WorkflowRuntime.validate_definition
  -> WorkflowDagContractValidator.validate
```

## 2. 根因

`WorkflowRuntime.validate_definition()` 原实现使用：

```python
if "edges" in definition:
    WorkflowDagContractValidator.validate(definition=definition)
```

这把普通顺序 Workflow 的 `edges: []` 当成了已经启用 DAG 的 Definition。

但同一 Runtime 的 `_resolve_dag_context()` 已明确使用：

```python
if not definition.get("edges"):
    return None
```

因此系统自身的 Runtime 语义已经把 `edges` 缺失或空数组定义为“未启用 DAG”。真正的 DAG Contract 只应在存在非空 edges 时执行。

## 3. 修复

将 DAG Contract 进入条件收敛为：

```python
if definition.get("edges"):
    WorkflowDagContractValidator.validate(definition=definition)
```

这样：

- `edges` 缺失：按顺序 Workflow 处理；
- `edges: []`：按顺序 Workflow 处理；
- `edges` 非空：进入 DAG Contract 严格校验；
- 非法 DAG 边、循环、孤立节点等规则仍由唯一的 `WorkflowDagContractValidator` 负责。

没有放宽 DAG Validator 本身的“非空 edges” Contract，也没有复制第二套 DAG 校验逻辑。

## 4. 回归覆盖

新增单元测试验证：

1. `edges: []` 可以通过 Runtime Definition 校验；
2. 非空但非法的 DAG edge 仍然抛出 `HTTPException(422)`。

## 5. 验收要求

代码提交后必须由开发者在本地执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
uv run python run_scheduler.py
```

Scheduler 验收重点不是“进程没有退出”，而是持续运行期间不再出现该 `DAG Workflow 必须包含非空 edges` 异常。

本错误记录不预填本地验收通过状态；最终结果以开发者实际执行输出为准。
