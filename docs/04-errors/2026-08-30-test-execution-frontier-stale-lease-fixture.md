# 测试误报：Execution Frontier 有效租约夹具使用历史时间

## 1. 现象

本地 Backend 全量测试在约 15% 之后出现首个确定性失败：

```text
tests/unit/test_execution_frontier_terminalization.py::test_terminal_execution_closes_owned_running_frontier_atomically[completed]
HTTPException: 409: Frontier Worker lease 已失效
```

当时测试进程的当前时间已经晚于测试夹具写死的 `2026-08-29 12:00`，而生产代码会使用当前 UTC 时间检查 Frontier lease，因此原本用于验证“有效 lease”的夹具实际构造出了“过期 lease”。

## 2. 根因

生产逻辑 `_terminalize_owned_frontier_for_execution()` 的 lease 校验本身没有发现异常：

```text
frontier.worker_lease_expires_at <= now
        ↓
拒绝 terminalization
```

问题出在单元测试数据：`_execution()` 与 `_frontier()` 使用固定历史时间作为有效租约。随着日期推进，该测试会从稳定通过变成稳定失败，形成与生产代码无关的确定性误报。

这类缺陷尤其危险，因为它会误导开发者修改生产 lease 校验，从而弱化 Runtime 的 fencing/lease 安全边界。

## 3. 修复

测试夹具改为基于当前 UTC 时间生成未来 5 分钟的有效 lease：

```text
now + 5 minutes
```

同时增加明确的过期 lease 反向测试，使用：

```text
now - 1 minute
```

并继续断言 terminalization 被拒绝且事务不会提交。

因此测试现在分别覆盖：

- 有效 lease → 允许 Execution/Frontier 原子终止；
- pending Frontier → 拒绝终止；
- 过期 lease → 拒绝终止。

生产代码未因本次测试修复而放宽任何 lease 校验。

## 4. 验证要求

本次修复完成后应按最小到完整顺序执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_execution_frontier_terminalization.py
uv run pytest -q --maxfail=1 -x --tb=long
uv run pytest -q
```

若单元测试通过但全量回归继续失败，应以新的首个失败为下一项根因分析对象，不得将本次测试误报视为全量通过。

## 5. 边界

本问题属于测试夹具时间基线错误，不属于 Runtime Alert、Workflow Execution 或 Durable Frontier 的生产逻辑缺陷。

本修复不修改状态机、lease/fencing 规则、事务边界或 Runtime 行为；仅修正测试数据语义并增加过期边界覆盖。
