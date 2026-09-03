# API Contract TestClient 在 Windows Proactor 下的未关闭传输警告

## 1. 问题

2026-09-04 本地 Backend 全量回归使用 `uv run pytest -q -W error -s` 时出现 1 个失败：

`tests/api_contract/test_api_workflows_endpoints.py::test_workflow_create_requires_bearer_authentication`

失败并非 HTTP Contract 断言错误，而是 pytest 将 Windows `asyncio` Proactor 的 `ResourceWarning` 升级为 `PytestUnraisableExceptionWarning`：

`ResourceWarning: unclosed transport <_ProactorSocketTransport ...>`

## 2. 根因

Workflow API Contract 测试模块在导入阶段创建全局 `TestClient(app)`，但没有显式关闭 Client。

在 Windows Proactor 事件循环实现下，TestClient 使用的传输对象生命周期可能晚于测试函数，在对象析构阶段才触发未关闭传输告警。由于项目统一要求 `-W error`，原本属于资源生命周期问题的警告被提升为测试失败。

这不是 Workflow 鉴权逻辑错误，也不是生产 API 需要增加网络清理代码；问题边界位于 Contract 测试的客户端生命周期管理。

## 3. 修复

将 Workflow API Contract 的全局 TestClient 改为模块级 pytest fixture，并使用上下文管理器创建：

```python
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
```

所有请求测试显式使用该 fixture，确保 TestClient 在模块测试结束时关闭底层传输。

## 4. 规则

- API Contract 测试不得依赖未关闭的全局 TestClient。
- Windows 环境必须把 `ResourceWarning` 视为真实工程问题，不能通过忽略 warning 或降低 `-W error` 规避。
- 测试资源生命周期必须与 fixture 生命周期一致。
- 不在生产 API 中加入仅用于掩盖测试资源泄漏的兼容清理逻辑。

## 5. 本地验证

```powershell
cd backend
uv run pytest -q -W error tests/api_contract/test_api_workflows_endpoints.py -s
uv run pytest -q -W error
```

本记录只描述根因与修复方案；在开发者本地重新执行上述命令并反馈前，不预填测试通过结果。
