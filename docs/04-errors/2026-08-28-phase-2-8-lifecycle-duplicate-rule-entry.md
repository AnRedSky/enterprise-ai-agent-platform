# Phase 2.8 Lifecycle 规则重复入口

- 日期：2026-08-28
- Phase：2.8 Multi-Agent Collaboration
- 类型：代码一致性 / Domain Rule Duplication
- 状态：待修正

## 1. 发现

深度核查远端 `main` 时发现：`backend/app/services/agent_delegation/lifecycle.py` 已定义 Delegation lifecycle 与 Worker completion fencing 的正式规则入口，但 `backend/app/services/agent_delegation/service.py` 仍保留独立的 `TERMINAL_STATES` / `TRANSITIONS` 常量，并由 `cancel()` 直接读取。

## 2. 影响

当前两份状态规则内容一致，因此尚未发现行为差异；但形成第二个业务规则入口，后续修改状态机时可能出现 Contract 漂移。该问题与开发准则中“相同业务规则只能保留一个正式计算/校验入口”的要求冲突。

## 3. 根因

`37061ab` 将生命周期与 fencing 抽取为独立纯领域入口时，只新增了 `lifecycle.py`，未同步删除 Service 内已有的重复状态常量及其调用。

## 4. 修复要求

在 Phase 2.8-B1 开发前：

1. 删除 `AgentDelegationService.TERMINAL_STATES` 与 `TRANSITIONS` 重复定义；
2. `cancel()` 改为调用 `lifecycle.validate_transition()`；
3. 全仓检索 Delegation 状态转换规则，确保不存在第三套正式实现；
4. 增加 targeted Unit / module-refactor 检查，防止重复入口回归。

## 5. 验收

修复完成后至少执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_agent_delegation_lifecycle.py
uv run pytest -q tests/unit -k delegation
uv run pytest -q
```

若进入 PostgreSQL Runtime，则继续执行对应 Integration / Real API Gate。未实际执行的结果不得记录为 Passed。
