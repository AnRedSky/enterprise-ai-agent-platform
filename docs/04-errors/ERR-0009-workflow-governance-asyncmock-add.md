# ERR-0009 — AsyncMock 错误模拟 AsyncSession.add

- Legacy ID: `005-workflow-governance-asyncmock-add-warning`
- Phase: 1.5-E

180 passed、4 warnings；`AsyncSession.add()` 是同步方法，但测试把整个 db Session 设置为 `AsyncMock`，导致 `db.add()` 返回未 await coroutine 并产生 RuntimeWarning。修复为 AsyncMock 仅覆盖异步方法，`db.add=Mock()`；生产代码不变。Backend Gate 要求最终 0 warning，修复后需重新验证。
