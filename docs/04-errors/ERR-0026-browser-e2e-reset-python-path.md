# ERR-0026 Browser E2E 数据库重置脚本直接执行时无法导入 app

## 1. 问题现象

Browser E2E 隔离 Gate 在执行本地数据库重置脚本时失败：

```text
ModuleNotFoundError: No module named 'app'
```

失败发生在 `backend/scripts/test/e2e/00_reset_browser_e2e_database.py` 导入 `app.core.config` 时。此前同一 Gate 在 Python 运行环境正确、数据库连接正常的前提下，仍无法进入数据库重置阶段。

## 2. 根因

Backend 测试配置通过 `pyproject.toml` 的 `pythonpath = ["."]` 为 pytest 提供 Backend 根目录导入路径，但 Browser E2E Gate 是直接执行独立 Python 脚本：

```text
uv run python .\\scripts\\test\\e2e\\00_reset_browser_e2e_database.py
```

直接执行脚本时，Python 默认将脚本所在目录加入 `sys.path`，不会因为 pytest 的 `pythonpath` 配置而自动加入 Backend 根目录。因此 `app` 包无法解析。

## 3. 修复

在数据库重置脚本启动阶段基于 `__file__` 定位 Backend 根目录，并在导入项目 `app` 包前显式加入 `sys.path`。

该修复只作用于 Browser E2E 测试基础设施，不改变生产运行时导入方式，也不引入兼容入口。

## 4. 预防

独立执行的 Backend Python 测试脚本不得假设 pytest 的 `pythonpath` 配置生效。凡由 PowerShell Gate 直接调用的 Python 脚本，必须能够在其约定工作目录下独立解析项目正式模块入口。

后续新增类似脚本时，应至少执行一次与 Gate 完全一致的直接命令验证，而不能仅通过 pytest 导入验证。

## 5. 验证边界

本次代码修复已提交到 `main`；开发者本地验证结果尚待用户按完整 Browser E2E Gate 实际执行后确认。
