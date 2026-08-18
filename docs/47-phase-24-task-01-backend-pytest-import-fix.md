# Phase 24 / Task 01：Backend pytest 导入环境修复完成记录

## 1. 上一阶段

Phase 23 / Task 07-C 已完成 Frontend 验证：`npm run build` 与 `npm test` 均由开发环境实际执行并通过。

## 2. 本阶段问题

在 `backend` 目录执行 `pytest -q`、HTTP Runtime RBAC 测试及 RBAC Matrix 测试时，测试收集阶段统一出现 `ModuleNotFoundError: No module named 'app'`。

17 个测试模块因此无法进入真正的测试执行阶段。

## 3. 根因

Backend 项目源码根目录为 `backend/app`，但 pytest 的测试收集环境没有稳定地将 `backend` 加入 Python import path。测试文件使用项目既定的绝对导入形式 `from app...`，因此在当前 Windows/Conda 执行环境下收集失败。

## 4. 修复

新增 `backend/tests/conftest.py`，在 pytest 收集阶段将 `backend` 根目录显式加入 `sys.path`。

该修复：

- 不修改业务代码；
- 不修改测试断言；
- 不降低测试严格程度；
- 不依赖开发者手工设置 `PYTHONPATH`；
- 同时兼容从 `backend` 或仓库根目录启动 pytest。

## 5. 验收要求

本次代码提交后，必须由开发环境人工执行：

```bash
cd backend
pytest -q
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

只有实际执行通过后，才允许将 Backend / Phase 24 Task 01 标记为 PASS。

## 6. Git

Commit message：`fix(backend): stabilize pytest app import path`
