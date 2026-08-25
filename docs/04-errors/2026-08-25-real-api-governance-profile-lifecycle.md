# 2026-08-25：Real API Governance 与 Model Profile 生命周期问题

## 1. 发生现象

本地 `01_backend_regression_gate.ps1` 在真实 HTTP API Gate 中出现两个 Retry Governance 断言失败：

```text
assert actions.index("workflow.node.retry_exhausted") < actions.index("workflow.execution.failed")
AssertionError: assert 2 < 1
```

同时 API 服务日志出现 Model Profile 删除 500：

```text
ForeignKeyViolationError:
update or delete on table "model_profiles" violates foreign key constraint
"model_usage_records_profile_id_fkey"
```

Worker 日志还曾出现：

```text
HTTPException: 409: Node 不允许从 running 到 running
```

## 2. 根因分析

### 2.1 Retry Governance

生产 Runtime 的语义是先记录 `workflow.node.retry_exhausted`，随后由统一 Execution 状态机推进 `workflow.execution.failed`。Runtime Governance 查询接口按 `created_at DESC, id DESC` 倒序返回审计记录。

原测试先 `reversed(audit_items)` 再判断顺序，实际把已经倒序的数据再次反转，导致断言方向与接口 Contract 不一致。

该问题属于测试断言错误，不应修改生产状态机或审计写入顺序。

### 2.2 Model Profile 删除

`model_usage_records.profile_id` 原来使用 `ON DELETE RESTRICT`，而用量记录同时保存了 `model_type`、`model_name`、价格版本、费率和成本快照。

这意味着历史用量已经具备独立审计所需的模型快照，不需要永久依赖当前 Model Profile 行。继续使用硬 RESTRICT 会导致 Profile 生命周期管理被历史用量永久阻塞，并在 API Service 未显式处理该约束时产生 500。

### 2.3 Worker `running → running`

该日志对应旧 Worker / Execution 继续推进已经处于 `running` 的节点。当前设计明确不把 `running → running` 视为合法状态，也不在本阶段偷偷增加 running Execution 自动 resume。

本轮 Scheduler / Worker Recovery Acceptance 已在 `fcf3326` 后通过，因此不因该历史日志放宽状态机。后续若再次出现，应结合 `worker_owner` / lease 信息判断是否为 stale consumer 或持久化恢复边界问题。

## 3. 修复方案

### Retry Governance

只修正 Real API 测试：按 Runtime Audit API 的倒序 Contract 直接比较：

```text
workflow.execution.failed
        ↓（接口倒序）
workflow.node.retry_exhausted
```

不改变生产 Runtime。

### Model Profile 生命周期

新增 Migration `0030_usage_profile_lifecycle`：

```text
model_usage_records.profile_id
    nullable = true
    ON DELETE SET NULL
```

删除 Profile 后：

```text
Model Profile 删除
       ↓
历史 ModelUsageRecord 保留
       ↓
profile_id = NULL
       ↓
model_type / model_name / pricing / cost 快照继续保留
```

这样既允许配置生命周期管理，也不破坏历史用量审计。

### Real API 回归

现有 Runtime Model Governance Real API 测试在真实 Provider 调用产生 Usage Record 后执行 cleanup，并明确断言 Profile / Provider 删除成功，以覆盖此前真实日志中的 FK 删除问题。

## 4. 服务生命周期约束

本轮所有 Real API / Scheduler / Worker 验收继续遵循：

- 测试脚本不得启动 API；
- 测试脚本不得启动 Scheduler；
- 测试脚本不得启动 Worker；
- 测试脚本不得停止或重启任何本地服务；
- 所需服务必须由开发者提前手动启动；
- Gate 只负责检查服务存在、执行测试并报告失败原因。

## 5. 防回归验证

本地必须在 `main` 最新代码上执行：

```powershell
cd backend
uv run pytest -q
uv run pytest -q tests/unit/test_workflow_execution_concurrency.py
uv run pytest -q tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker.py
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

其中后三个真实链路 Gate 的前置服务必须手动启动；脚本不得代为启动、停止或重启。

## 6. 验收判定

本次代码提交完成后不能预填“通过”。必须以开发者本地实际执行结果作为最终验收依据。
