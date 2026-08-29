# Phase 2.9-C Durable Delivery 数据库导入错误

## 1. 问题

开发者本地执行 Phase 2.9-C 定向测试时，三个测试模块在 collection 阶段同时失败：

```text
ModuleNotFoundError: No module named 'app.core.database'
```

错误入口为 `backend/app/services/integration/delivery.py`。

## 2. 根因

项目数据库基础设施已经按模块化规则迁移到：

```text
app/infrastructure/db/session.py
app/infrastructure/db/__init__.py
```

其中 `SessionLocal` 正式由 `app.infrastructure.db` 暴露；项目不存在 `app.core.database` 模块。

Phase 2.9-C Delivery Service 在新增时错误引用了旧的、项目不存在的数据库路径，导致任何导入 `app.services.integration` 的测试在 collection 阶段直接失败。

## 3. 修复

将：

```python
from app.core.database import SessionLocal
```

修正为：

```python
from app.infrastructure.db import SessionLocal
```

同时补强 Delivery Service 单元测试，使其实际覆盖：

- 无可领取事件时不调用 Sender；
- Claim 成功后先提交租约事务；
- Sender 成功后写入 delivered；
- Sender 异常后写入 retry 信息；
- 单元测试使用 SessionLocal 替身，不依赖真实 PostgreSQL。

## 4. 验证边界

开发者反馈的 `uv run alembic upgrade head` 已成功从 `0040` 升级到 `0041`，并且 `uv run alembic current` 已确认 `0041_integration_event_delivery_lease` 为 head。

原定向测试在修复前无法完成 collection，因此修复后的测试结果必须由开发者本地重新执行后记录，不预填通过结论。

## 5. 预防措施

后续新增领域模块必须先检索正式 Infrastructure 入口，禁止根据旧项目结构猜测数据库、缓存或 Provider 路径。涉及模块迁移时必须同步执行旧路径搜索和 targeted import test。
