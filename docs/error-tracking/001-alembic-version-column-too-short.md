# 001：Alembic revision id 超过 version_num 长度

## 1. 基本信息

- 阶段：Phase 1.5-C Workflow Execution State Machine
- 日期：2026-08-19
- 类型：Database Migration / Alembic
- 严重级别：阻塞
- 影响范围：`uv run alembic upgrade head`

## 2. 实际错误

执行：

```powershell
cd backend
uv run alembic upgrade head
```

在执行 `0015_tenant_contract -> 0016_workflow_execution_state_machine` 时失败：

```text
asyncpg.exceptions.StringDataRightTruncationError:
value too long for type character varying(32)

UPDATE alembic_version
SET version_num='0016_workflow_execution_state_machine'
WHERE alembic_version.version_num = '0015_tenant_contract'
```

## 3. 根因

历史 Alembic 版本表的 `version_num` 列定义为 `VARCHAR(32)`，而新的 revision id：

```text
0016_workflow_execution_state_machine
```

长度为 37 个字符，因此 PostgreSQL 在 Alembic 完成 migration 后写入新 head revision 时发生截断异常。

该错误不是 Workflow Execution 表结构本身的问题，而是 **migration revision metadata schema 与 revision naming convention 不兼容**。

## 4. 实际修复方案

当前 0016 migration 文件本身不修改历史 Alembic metadata schema；兼容逻辑放在统一的 `backend/alembic/env.py` migration preflight 中：

1. 检查 `public.alembic_version` 是否已经存在。
2. 检查 `version_num` 的实际长度。
3. 当历史长度小于 64 时，在 Alembic migration transaction 内执行：

```sql
ALTER TABLE alembic_version
ALTER COLUMN version_num TYPE VARCHAR(64)
```

4. 然后继续执行正常 Alembic migration。
5. 新数据库尚不存在 `alembic_version` 时不执行任何操作，由 Alembic 正常创建版本表。

这样既兼容已有 `0015` 数据库，也不要求修改已经存在的 migration revision history。

## 5. 预防措施

- 新增 Alembic revision 前检查 revision id 长度。
- 不再假设历史 `alembic_version.version_num` 可以容纳任意新 revision id。
- Migration 测试必须覆盖 `upgrade head`，不能只测试业务表是否创建成功。
- 统一以 `VARCHAR(64)` 作为 revision metadata 容量基线。
- 任何 migration failure 必须记录到 `docs/error-tracking/`。
- Migration 相关变更完成后，必须实际执行 `uv run alembic upgrade head`，结果未执行前不得标记通过。
- 新增 `backend/tests/test_alembic_env.py`，覆盖扩展、缺表 no-op、已有足够长度 no-op 三种场景。

## 6. 验证要求

修复后必须由开发者本地实际执行：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_c_workflow_execution_validation.ps1
```

如果数据库已经停留在 `0015_tenant_contract`，直接执行 `upgrade head`；如果本地数据库状态不一致，先确认 `alembic current`，禁止通过删除 migration history 的方式掩盖问题。

## 7. 状态

修复代码已提交 `main`；**尚未由开发者本地重新执行上述命令，因此不能记录为“验证通过”**。
