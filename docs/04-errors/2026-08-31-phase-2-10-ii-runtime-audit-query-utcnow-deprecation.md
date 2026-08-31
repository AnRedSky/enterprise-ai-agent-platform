# Runtime Audit Query 真实验收时间 API 弃用警告

- 日期：2026-08-31
- 阶段：Phase 2.10-II / II-06
- 现象：`tests/api_real/test_runtime_audit_query_acceptance.py` 使用 `datetime.utcnow()`，pytest 真实 PostgreSQL 验收出现 `DeprecationWarning`。
- 根因：Python 新版本已将无时区的 `datetime.utcnow()` 标记为弃用；项目 Runtime 时间规则统一要求使用明确的 UTC 时间语义。
- 修复：测试夹具改为 `datetime.now(UTC).replace(tzinfo=None)`，保持数据库现有 `DateTime` 无时区字段兼容，同时显式表达“当前 UTC 时间”。
- 影响：不改变业务事实、不改变查询 Contract，仅消除测试层弃用警告并与生产代码的 UTC 时间约定保持一致。
- 验证：应重新执行 II-06 Unit Gate、Real Gate 与 Backend Regression；在本次远程源码修改环境中未冒充本地执行结果。
