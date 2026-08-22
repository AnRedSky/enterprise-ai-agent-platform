# ERR-0018 — Organization Membership Migration SQLAlchemy bind parser

## 1. 现象

Phase 2.1-B 本地执行：

```text
uv run alembic upgrade head
```

在 `0023_organization_membership` 执行 membership backfill 时失败：

```text
sqlalchemy.exc.InvalidRequestError:
A value is required for bind parameter 'organization'
```

## 2. 根因

Alembic migration 使用 `op.execute(sa.text(...))` 执行 PostgreSQL SQL。SQL 字符串中的：

```sql
':organization-membership'
```

被 SQLAlchemy `text()` 解析器误认为 bind parameter `:organization`，而 migration 没有提供对应参数，因此 SQL 尚未到达 PostgreSQL 即在 SQLAlchemy 编译阶段失败。

## 3. 修复

将 deterministic UUID seed 字符串调整为不包含 `:` 的固定字符串：

```sql
'organization-membership'
```

保留 deterministic UUID 语义，不改变 Organization / Membership 数据映射规则。

同时在本轮 2.1-C API 实现中固定了 Organization / Membership 创建时显式生成 UUID，避免依赖 SQLAlchemy flush 后默认值回填外键。

## 4. 验证

用户本地实际验证：

```text
uv run alembic upgrade head
Running upgrade 0022_workflow_trigger -> 0023_organization_membership

uv run alembic heads
0023_organization_membership (head)
```

Migration 已成功完成。

## 5. 影响范围

- Phase：2.1-B
- Component：Alembic / PostgreSQL migration
- Severity：阻塞本地 Migration Gate
- 状态：**已修复并验证**

## 6. 设计教训

使用 SQLAlchemy `text()` 承载 PostgreSQL 字符串字面量时，必须避免无意触发 `:name` bind parameter 解析；确定性 seed 字符串应使用不会产生 bind parser 歧义的格式。
