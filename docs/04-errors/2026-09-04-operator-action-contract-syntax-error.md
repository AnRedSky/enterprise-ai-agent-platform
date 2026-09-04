# Operator Action API Contract 测试语法错误

## 1. 问题

2026-09-04 本地执行 Operator Action API Contract Gate 时，`backend/tests/api_contract/test_api_operator_actions.py` 在 pytest collection 阶段直接失败：

```text
SyntaxError: unexpected character after line continuation character
```

失败位置为 `auth_headers` fixture 的 Token 生成表达式。

## 2. 根因

测试源码在 f-string 表达式内部保留了不应存在的反斜杠转义：

```python
create_token(actor_id, [\"user\"], tenant_id=tenant_id)
```

Python 解析 f-string 表达式时将反斜杠识别为非法字符，因此测试尚未进入任何断言或应用代码就发生 collection 级语法错误。

该问题属于测试源码生成/写入错误，不是 FastAPI、JWT 鉴权、Operator Governance 或生产运行时逻辑故障。

## 3. 修复

将 Token 生成拆为普通局部变量，避免 f-string 表达式内部出现转义字符：

```python
token = create_token(actor_id, ["user"], tenant_id=tenant_id)
return {"Authorization": f"Bearer {token}"}
```

同时保持测试身份由 `uuid4()` 自动生成，不要求人工填写用户、租户或 Token 数据。

## 4. 验证要求

修复后必须重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-contract\01_operator_action_contract.ps1
uv run pytest -q -W error tests/api_contract/test_api_operator_actions.py tests/api_contract/test_api_workflows_endpoints.py -s
$env:PYTHONTRACEMALLOC="25"
uv run pytest -q -W error -s
Remove-Item Env:PYTHONTRACEMALLOC -ErrorAction SilentlyContinue
uv run alembic upgrade head
```

本错误记录不预填修复后的测试通过结果；最终结果以开发者本地实际执行输出为准。

## 5. 服务边界

Operator Action API Contract Gate 使用 ASGI transport，不自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL 或 Redis。真实 PostgreSQL / Real API 验收继续由对应独立 Gate 负责。
