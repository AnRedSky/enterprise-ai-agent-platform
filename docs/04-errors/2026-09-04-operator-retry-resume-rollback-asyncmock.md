# Operator Retry / Resume 回滚验收 AsyncMock NameError

## 1. 发生时间

2026-09-04

## 2. 现象

本地执行：

```powershell
uv run pytest -q -W error tests/integration/test_operator_execution_retry_resume_concurrency.py -s
```

结果为：

```text
2 passed, 2 failed
```

两个失败均发生在新增 Retry / Resume 最终化失败回滚测试，异常为：

```text
NameError: name 'AsyncMock' is not defined
```

## 3. 根因

测试新增了 `AsyncMock` 以模拟 Operator Audit 最终化失败，但测试模块缺少：

```python
from unittest.mock import AsyncMock
```

同时测试函数声明了 `monkeypatch` fixture，却直接给实例属性赋值，未实际使用该 fixture。

## 4. 修复

1. 补充 `unittest.mock.AsyncMock` 正式导入；
2. 使用 `monkeypatch.setattr(service, "_audit", AsyncMock(...))` 注入失败行为；
3. 保持测试不启动 API、Worker、Scheduler、PostgreSQL 或 Redis；
4. 保持测试数据由 fixture 自动创建和清理。

## 5. 验证要求

修复后的本地真实 PostgreSQL 验收必须重新执行：

```powershell
$env:RUN_DATABASE_INTEGRATION="1"
uv run pytest -q -W error tests/integration/test_operator_execution_retry_resume_concurrency.py -s
```

然后执行完整 Operator Governance Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
```

本错误记录不将修复后的代码提交状态等同于真实 PostgreSQL 测试通过；最终结果以开发者本地执行输出为准。
