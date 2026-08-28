# Phase 2.8-B1 Real API 测试 AsyncEngine 事件循环隔离

- 日期：2026-08-28
- Phase：2.8 Multi-Agent Collaboration
- 类型：测试基础设施 / AsyncEngine 生命周期
- 状态：已修正，待本地验证

## 1. 发现

B1 新增真实 PostgreSQL 并发测试后，发现测试最初在同一个同步测试函数内多次调用 `asyncio.run()`。项目使用全局 SQLAlchemy `AsyncEngine` / `SessionLocal`，不同 `asyncio.run()` 会创建不同事件循环；连接池可能复用绑定旧事件循环的 asyncpg connection。

## 2. 风险

可能出现 `Event loop is closed`、asyncpg connection 绑定旧事件循环或 Windows Proactor 相关异步清理告警。该问题不是 B1 业务代码本身的并发缺陷，但会让真实 PostgreSQL 并发验收产生非确定性失败。

## 3. 修复

已将 B1 Real API 测试改为 `pytest.mark.asyncio` 的单一测试事件循环：

- 同一测试事件循环内完成 HTTP fixture 创建后的数据库读取；
- 两个独立 `AsyncSession` 仍保持真正并发竞争；
- 持久化校验与第二次 Claim 也在同一事件循环完成；
- 复用现有 `tests/conftest.py` 的 Real API engine dispose 生命周期隔离。

## 4. 验收

必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q tests/api_real/test_agent_delegation_claim_api.py
```

然后执行 Phase 2.8 完整 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

未执行前不得记录为 Passed。
