# 2026-08-25 Workflow 发布 Contract 收紧后的历史测试数据兼容

## 1. 现象

Backend 回归在 `tests/unit/test_workflow_publish_governance.py` 出现 2 个失败：

```text
Workflow definition 必须包含非空 nodes
Workflow node 必须为对象
```

失败 fixture 分别使用了历史 Definition 形态：

```json
{"nodes": []}
{"nodes": ["new"]}
```

## 2. 根因

`WorkflowRegistry.publish()` 已在发布边界复用唯一 `WorkflowRuntime.validate_definition()`。新的 Runtime Contract 要求：

- `nodes` 必须非空；
- 每个 node 必须为对象；
- node 必须包含合法 `id` / `type`；
- node config 与 Runtime timeout / retry / circuit breaker 配置必须合法。

因此旧的 Workflow 发布单元测试 fixture 不再代表当前“新版本发布”契约。

## 3. 兼容边界

本次不降低新的 Runtime Contract，也不允许历史非法 Definition 再次进入 `published` 状态。

兼容规则明确为：

```text
历史已 published + 当前仍为 published_version
        -> 允许幂等确认 / 读取
        -> 不重新校验旧 Definition

新的 draft/testing -> published
        -> 必须通过当前 Runtime Definition Contract
        -> 空 nodes / 字符串 node 等旧格式一律拒绝
```

原因是历史记录属于审计与版本历史的一部分，不能因为 Contract 升级而要求历史数据全部重写；但历史数据也不能通过重新发布路径重新成为新的执行输入。

该兼容边界与 `WorkflowRegistry.publish()` 的现有幂等分支一致，新增中文注释明确其设计意图，并增加单元测试锁定行为。

## 4. 修复

- 将 `test_publish_sets_active_version_and_is_idempotent` 的新版本 fixture 改为合法 Runtime Definition。
- 将 `test_publish_deprecates_previous_active_version` 的当前版本 fixture 改为合法 Runtime Definition；previous published 版本保留历史空 `nodes` 形态，用于覆盖真实兼容场景。
- 新增 `test_publish_keeps_historical_published_legacy_definition_idempotent`，验证历史已发布旧 Definition 可以幂等确认，不触发 commit 或新的 AuditLog。
- 保留 `WorkflowRuntime.validate_definition()` 作为唯一的新版本发布校验入口。

## 5. 验证要求

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_publish_governance.py
uv run pytest -q
```

如果需要完整发布前验证，再执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

以上命令只定义可重复的自动化验证入口；实际通过状态以开发者本地执行结果为准。

## 6. 不变边界

本修复不修改 Scheduler 的 slot、lease、misfire、idempotency、tenant isolation、restart recovery，也不新增第二套 Definition Validator。
