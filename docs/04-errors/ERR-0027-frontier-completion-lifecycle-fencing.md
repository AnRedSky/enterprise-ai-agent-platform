# ERR-0027：Frontier completion 将目标状态误作当前 lifecycle，遮蔽 stale Worker fencing

## 1. 问题现象

2026-08-28 本地执行 Durable Resume / Execution / DAG / Frontier targeted regression 时，`tests/unit/test_frontier_claim_completion_fencing.py` 的两个 stale Worker completion 用例失败。

实际异常先返回：`Frontier progression 的 Execution lifecycle 与目标不一致: 当前=running, 目标=completed`，导致测试期望的 `Worker ownership 已失效` 与 `Worker lease 已失效` 没有机会执行。

## 2. 根因

`complete_frontier_with_checkpoint()` 同时使用 `execution_status` 表示“本次 completion fact 写入后的目标状态”和“进入 Frontier completion 前 Execution 必须处于的当前状态”。

当当前 Frontier 无 Next Frontier 时，`execution_status` 必然为 `completed`，但 completion 操作开始时 Execution 仍然必须是 `running`。因此直接比较 `execution.status != execution_status` 会在 ownership / lease fencing 之前错误拒绝正常的 terminal completion，也会遮蔽 stale Worker 的真实失败原因。

## 3. 修复

将 progression 前的 lifecycle guard 明确固定为 `execution.status == "running"`；保留 `execution_status` 作为 Checkpoint / terminalization 的结果状态。

校验顺序调整为：

1. 锁定并确认 Execution 当前为 `running`；
2. 校验 Execution Worker ownership；
3. 校验 Execution Worker lease；
4. terminal completion 时检查 sibling Frontier；
5. 执行 Frontier ownership transition；
6. 按目标状态写入 Checkpoint / Execution terminal fact。

这样既不放宽 stale Worker fencing，也不会让 terminal target 与当前 lifecycle 的正常差异遮蔽 ownership / lease 失效。

## 4. 验证边界

本次修复提交：`8834ca0edcb3a9576eaf55c75943828bf4083228`。

代码已提交到 `main`，但必须以开发者下一次本地实际执行结果确认通过；本记录不将尚未执行的结果标记为 PASS。

建议首先重新执行：

```powershell
cd backend
uv run pytest -q `
  tests/unit/test_frontier_duplicate_completion.py `
  tests/unit/test_frontier_duplicate_consumption.py `
  tests/unit/test_frontier_failure_terminalization.py `
  tests/unit/test_frontier_failure_transaction.py `
  tests/unit/test_frontier_claim_completion_fencing.py
```

然后执行完整 targeted regression：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\workflow\01_resume_runtime_regression.ps1
```

## 5. 预防

- 明确区分“当前 lifecycle”与“本次 Durable fact 的目标 lifecycle”。
- ownership / lease fencing 必须在允许写入 Frontier completion 前生效。
- 非显然的状态机、租约和并发规则必须在生产代码附近记录设计意图。
- 测试 double 必须同时表达当前 lifecycle 与目标 checkpoint lifecycle，禁止通过修改生产约束迁就 fixture。
