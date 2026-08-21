# ERR-0002 — Alembic env 测试错误导入

- Legacy ID: `002-alembic-env-test-import`
- Phase: 1.5-C
- 类型: Backend Test / Alembic Testability
- 严重级别: 阻塞

## 现象
`tests/test_alembic_env.py` 使用 `from alembic import env`，测试收集失败：`ImportError: cannot import name 'env' from 'alembic'`。

## 根因
migration entrypoint 不是普通业务 Python 模块，直接 import 会触发 Alembic context 副作用。

## 修复
将纯数据库兼容逻辑抽到 `backend/app/core/alembic_compat.py`，`alembic/env.py` 只负责 migration lifecycle；测试直接覆盖兼容函数。

## 验证
必须实际执行 pytest、`alembic upgrade head/current` 和 Phase 1.5-C validation；原记录未预填通过结果。
