# 2026-08-26 pytest-asyncio 事件循环关闭回归

## 1. 现象

在 `c8d97b1` 之后执行 Backend 全量回归时出现 11 个 setup error：

```text
RuntimeError: Event loop is closed

self = <ProactorEventLoop running=False closed=True debug=False>
```

同时出现以下警告：

- pytest-asyncio 检测到 teardown 阶段存在未关闭事件循环；
- async fixture setup coroutine 未被 await；
- SQLAlchemy result 处理过程中出现未 await coroutine 警告。

本地反馈基线：

```text
459 passed, 3 skipped, 41 deselected, 4 warnings, 11 errors in 32.37s
```

## 2. 根因

项目 `backend/pyproject.toml` 原先设置：

```toml
asyncio_default_fixture_loop_scope = "session"
```

而大量测试使用 `@pytest.mark.asyncio`，测试本身按函数级事件循环执行。此前 `tests/conftest.py` 又新增了函数级 autouse fixture，并显式使用：

```python
@pytest_asyncio.fixture(autouse=True, loop_scope="function")
```

这使异步 fixture 的生命周期同时存在 session loop 与 function loop 两套语义。当 session-scoped async fixture / fixture wrapper 持有的事件循环已经由 pytest-asyncio teardown 后，后续 fixture setup 仍尝试向该 loop 创建 task，最终触发 `Event loop is closed`。

该问题不是 Workflow Worker、Scheduler 或业务 Runtime 的生产代码错误，而是 pytest-asyncio fixture loop scope 配置与测试生命周期不一致导致的测试基础设施回归。

## 3. 修复原则

将 Backend pytest 默认 async fixture loop scope 从 `session` 调整为 `function`：

```toml
asyncio_default_fixture_loop_scope = "function"
```

这样默认 async fixture 与函数级测试共享同一事件循环生命周期；SQLAlchemy AsyncEngine 的连接池不会跨测试 loop 复用已绑定连接。

保留 `tests/conftest.py` 中真实 API 场景的 function-scope engine dispose 约束，用于进一步隔离真实 API 测试数据库连接池。

## 4. 验证要求

修复后必须在本地执行：

```powershell
cd backend
uv run pytest -q
```

并重点确认：

1. 0 errors；
2. 0 `Event loop is closed`；
3. 0 pytest-asyncio unclosed event loop warning；
4. 0 `coroutine ... was never awaited` warning；
5. 原有 Workflow / Worker / DAG Resume targeted tests 不回归。

在默认 regression 全绿之前，不得把 Phase 2.6 当前 Runtime Integration 标记为进一步完成。

## 5. 与 Worker 手动运行日志的关系

本次反馈中的以下 Worker 日志属于运行时失败场景，不作为本事件循环回归的根因：

- Mock provider 返回 HTTP 404；
- OpenAI-compatible provider endpoint 返回 HTTP 503；
- Workflow Agent 不存在返回 HTTP 404。

这些错误应在对应真实 Provider / Workflow 配置和失败路径验收中单独处理，不能通过吞掉异常或降低日志级别掩盖。
