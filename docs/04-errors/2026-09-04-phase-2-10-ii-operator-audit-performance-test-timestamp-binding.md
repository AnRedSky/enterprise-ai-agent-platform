# 2026-09-04 Phase 2.10-II Operator Audit 性能验收时间参数绑定错误

## 1. 问题现象

Backend 全量回归在 `tests/api_real/test_operator_audit_query_performance_acceptance.py` 的 action 查询计划验收中失败：PostgreSQL `created_at` 参数通过 asyncpg 执行时收到字符串，触发 `DataError`。

典型错误为：`expected a datetime.date or datetime.datetime instance, got 'str'`。

## 2. 根因分析

新增的查询计划验收测试使用 SQLAlchemy `text()` + asyncpg 执行带 `created_at >= :since` 的 PostgreSQL 查询，但测试夹具将 `since` 定义为 ISO-8601 字符串。

asyncpg 对已推断为 PostgreSQL 时间类型的绑定参数要求传入 Python `datetime`/`date` 对象，而不是字符串。因此问题属于测试实现的参数类型错误，不是 Operator Audit 生产查询、Repository 或数据库索引实现错误。

## 3. 修复

将性能验收测试的固定时间夹具改为带 UTC 时区的 Python `datetime`：`datetime(2026, 1, 1, tzinfo=timezone.utc)`，并将参数类型从 `dict[str, str]` 放宽为 `dict[str, object]`，保持其他查询参数不变。

该测试仍然：

- 只执行 `EXPLAIN (COSTS OFF)`；
- 不写入业务数据；
- 不启动、重启或停止任何服务；
- 使用 `SET LOCAL enable_seqscan = off` 验证 Canonical 索引可被查询计划使用；
- 覆盖 action、actor、resource、execution、trace、operator_action 六条正式查询路径。

## 4. 验证要求

本次修复已提交到 `main`。开发者本地必须重新执行 Backend 全量回归，并重点执行 Phase 2.10-II Operator Audit Performance Gate，确认六条查询计划验收全部实际执行通过。

本记录不把尚未由本地重新执行得到的结果预填为通过。
