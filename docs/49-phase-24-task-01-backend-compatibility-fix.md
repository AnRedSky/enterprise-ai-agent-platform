# Phase 24 Task 01：Backend pytest 导入与运行时兼容性修复

## 1. 完成内容

本轮针对 Windows + Anaconda 环境执行 `backend/pytest -q` 时暴露的 10 个 collection errors 进行修复。

主要问题：

- `app.core.config` 缺失，导致 Model Gateway 无法导入。
- `app.api.dependencies` 缺失，导致 Runtime HTTP RBAC 测试无法导入 `get_db`。
- `app.models.audit` 缺失，而 Runtime Query Service 仍依赖兼容路径。
- `HTTPRedirectHandler` 从错误的 `urllib.error` 模块导入。

## 2. 修复结果

新增：

- `backend/app/core/config.py`
- `backend/app/api/dependencies.py`
- `backend/app/models/audit.py`

修复：

- `backend/app/tools/http_executor.py`

## 3. 未掩盖的问题

`passlib[bcrypt]` 已在 `backend/requirements.txt` 中声明，但当前执行测试的本地 Python 环境报告 `ModuleNotFoundError: No module named 'passlib'`。该项属于本地依赖未安装，不通过修改业务代码绕过。

## 4. 下一步验证

同步最新 `main` 后重新执行：

```bash
cd backend
python -m pip install -r requirements.txt
pytest -q
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

只有实际测试通过后，才将 Phase 24 Task 01 标记为最终通过。
