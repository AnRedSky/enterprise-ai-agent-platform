# 2026-08-24 Scheduler misfire 循环导入

## 1. 现象

提交 `09b3811` 集成 tenant isolation 与 misfire policy 后，开发者本地执行应用导入时失败：

```text
ImportError: cannot import name 'build_schedule_slot' from partially initialized module
'app.services.workflow_scheduler.contract'
```

调用链为：

```text
workflow_scheduler.__init__
  → contract.py
  → misfire.py
  → contract.py
```

因此 `app.main` 无法导入，`04_scheduler_tenant_misfire_gate.ps1`、Real API tenant-safe bootstrap 以及完整 `pytest` 均在收集/启动阶段失败。

## 2. 根因

`contract.py` 已经只是 Scheduler 各职责模块的公开聚合入口，但 `misfire.py` 仍反向从 `contract.py` 导入 `build_schedule_slot`，形成：

```text
contract → misfire → contract
```

这违反了 Scheduler 子模块单向依赖原则，也使新的 misfire 集成破坏了应用启动路径。

## 3. 修复

将 `misfire.py` 的 `build_schedule_slot` import 改为直接依赖其职责归属模块：

```python
from .time import build_schedule_slot
```

同时修正模块说明，使关键依赖明确指向 Scheduler 模型与统一时间槽位构造函数，而不是把 `contract.py` 误写成底层依赖。

该修复不新增 Scheduler、Repository、Provider 或 misfire 第二套实现，仅修正 canonical 模块之间的依赖方向。

## 4. 验证要求

修复提交后必须由开发者本地重新执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\05_backend_refactor_closure_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
uv run pytest -q
```

在开发者重新执行前，不将上述结果记录为通过。
