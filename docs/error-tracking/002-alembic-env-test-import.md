# 002：Alembic env 测试错误导入包模块

## 1. 基本信息

- 阶段：Phase 1.5-C Workflow Execution State Machine
- 日期：2026-08-19
- 类型：Backend Test / Alembic Testability
- 严重级别：阻塞
- 影响范围：`uv run pytest -q`、1.5-C Backend 全量回归

## 2. 实际错误

开发者本地执行：

```powershell
cd backend
uv run pytest -q
```

以及：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_c_workflow_execution_validation.ps1
```

均在测试收集阶段失败：

```text
ImportError: cannot import name 'env' from 'alembic'
```

失败文件：

```text
tests/test_alembic_env.py
```

原测试直接使用：

```python
from alembic import env
```

但 `backend/alembic/env.py` 是 Alembic migration script，不是 `alembic` Python 包中的可导入 `env` 模块。

## 3. 根因

测试为了覆盖 `backend/alembic/env.py` 内的 `_prepare_alembic_version_table()`，直接将 migration script 当作应用模块导入。

该 migration script 在导入时还会读取 Alembic `context` 并根据 offline / online 模式执行 migration 入口，因此不适合作为普通业务 Python 模块被 pytest 直接 import。

这造成两个问题：

1. `from alembic import env` 本身无法解析；
2. 即使通过动态 import 强行加载，也容易触发 migration script 的运行时副作用。

## 4. 修复方案

将纯数据库兼容逻辑从 migration entrypoint 中独立到：

```text
backend/app/core/alembic_compat.py
```

由该模块提供：

```python
prepare_alembic_version_table(connection)
```

`backend/alembic/env.py` 仅负责 Alembic migration lifecycle，并调用该兼容函数。

测试改为直接测试 `app.core.alembic_compat.prepare_alembic_version_table`，避免 import migration entrypoint，也避免测试触发真实 migration 副作用。

## 5. 预防措施

- 不得把 `backend/alembic/*.py` migration entrypoint 当作普通应用模块直接 import 测试。
- Alembic migration 中可复用、可单测的纯逻辑应提取到 `backend/app/core/` 等应用模块。
- Backend 测试必须通过 `uv run pytest -q` 实际执行并通过后才能进入下一阶段。
- Migration 仍必须通过 `uv run alembic upgrade head` 和 `uv run alembic current` 实际验证。
- 新发生的工程错误继续独立记录在 `docs/error-tracking/`。

## 6. 验证要求

修复提交后由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_c_workflow_execution_validation.ps1
```

未收到实际执行结果前，不得标记 Phase 1.5-C 为验收通过。

## 7. 状态

代码修复已提交 `main` 后，等待开发者重新执行上述本地验证；当前不能记录为验证通过。
