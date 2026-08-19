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

## 4. 修复原则

在 `0016` migration 开始执行时，先将：

```text
alembic_version.version_num
VARCHAR(32) → VARCHAR(64)
```

然后再创建 Workflow Execution / Node Execution 表。

Migration downgrade 时，在目标 revision 已回退到历史短 revision 后再恢复为 `VARCHAR(32)`，确保旧 schema 与 downgrade 顺序兼容。

## 5. 预防措施

- 新增 Alembic revision 前检查 revision id 长度。
- 不再假设历史 `alembic_version.version_num` 可以容纳任意新 revision id。
- Migration 测试必须覆盖 `upgrade head`，不能只测试业务表是否创建成功。
- 长期保留 `VARCHAR(64)` 作为 revision metadata 的容量基线。
- 任何 migration failure 必须记录到 `docs/error-tracking/`。
- Migration 相关变更完成后，必须实际执行 `uv run alembic upgrade head`，结果未执行前不得标记通过。

## 6. 验证要求

修复后必须由开发者本地实际执行：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run pytest -q
```

如果数据库已经停留在 `0015_tenant_contract`，直接执行 `upgrade head`；如果本地数据库状态不一致，先确认 `alembic current`，禁止通过删除 migration history 的方式掩盖问题。

## 7. 状态

代码修复已准备；本记录中的“验证通过”必须以开发者实际反馈为准。
