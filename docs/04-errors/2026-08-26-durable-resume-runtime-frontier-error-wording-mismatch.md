# Durable Resume Runtime 多 frontier 错误文案契约不一致

## 发生时间

2026-08-26

## 现象

DAG Resume Runtime 已将多 frontier 校验统一委托给 `WorkflowDagResumeRuntimePlanner`，但生产异常文案从原先测试与调用方约定的 frontier 表述发生了漂移。

已有 targeted tests 分别依赖：

- Sequence Planner：错误信息包含 `多个 frontier`；
- WorkflowRuntime Resume：错误信息包含 `多个 frontier`；
- Runtime Planner：错误信息包含 `多个分支需要先冻结状态合并 Contract`。

修复前实际文案为：

`DAG Resume Runtime 当前只允许单一 frontier Node，多个分支需要先冻结状态合并 Contract`

该文案缺少连续的 `多个 frontier` 片段，因此虽然语义正确，但无法满足已经冻结的错误边界测试。

## 根因

Runtime Planner 的异常信息只表达了“单一 frontier + 多个分支”的语义，没有保留调用方已经使用的两个稳定关键词边界。随着 Sequence Planner 改为完全委托 Runtime Planner，底层异常直接成为上层可观察错误，导致两个层级的测试契约同时暴露不一致。

## 修复

统一 Runtime Planner 的多 frontier 异常文案为同时包含两个既有契约片段：

`DAG Resume Runtime 当前只允许单一 frontier Node；当前存在多个 frontier，多个分支需要先冻结状态合并 Contract`

这样既明确指出当前拒绝原因是多个 frontier，又保留分支状态合并 Contract 尚未冻结的设计边界；Sequence Planner 和 WorkflowRuntime 无需复制或包装另一套 frontier 规则。

## 验证要求

开发者必须在本地最新 `main` 上执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_dag_runtime.py tests/unit/test_workflow_dag_runtime_sequence.py tests/unit/test_workflow_runtime_resume.py
uv run pytest -q
```

预期第一条 targeted 命令覆盖 Runtime Planner、Sequence Planner、WorkflowRuntime Resume 的错误边界；第二条执行完整 Backend Regression。以上“通过”状态只能依据开发者实际执行结果记录，不得预填。

## 设计边界

本次修复只统一错误文案，不改变 DAG frontier 计算、Resume 状态传递、Worker ownership、Checkpoint 持久化或分支状态合并策略。第一版 Runtime 仍明确拒绝多个 frontier；在分支状态合并 Contract 冻结前不得通过顺序执行伪装支持 DAG 分支恢复。
