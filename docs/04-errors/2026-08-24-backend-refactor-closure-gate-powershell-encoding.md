# 工程错误记录：Refactor Closure Gate 中文标记在 Windows PowerShell 管道中发生编码损坏

## 发生时间

2026-08-24

## 现象

用户在 Windows PowerShell 本地执行 `05_backend_refactor_closure_gate.ps1` 时，模块职责说明校验对应的内嵌 Python 代码被错误转换为 `?????` 等非预期字符，最终产生 Python `SyntaxError`，Gate 以 `Canonical module description validation failed.` 退出。

同一版本的 API v1、Runtime Boundary、Module Refactor、Dependency Boundary 与 Backend Regression 均已由用户本地反馈通过，因此该失败集中在 Closure Gate 的 Windows 编码处理，而不是业务模块重构回归。

## 根因

Closure Gate 通过 PowerShell here-string 将中文字符串 `职责：`、`边界：` 直接管道传递给 `uv run python -`。在部分 Windows PowerShell 代码页环境下，管道传输破坏了内嵌 Python 源码中的中文字符串字面量，导致 Python 解析失败。

## 修复

将 Gate 的中文职责/边界标记检查改为 Python Unicode 转义：

```python
required_markers = ("\\u804c\\u8d23\\uff1a", "\\u8fb9\\u754c\\uff1a")
```

同时保留实际模块文件以 UTF-8 读取，校验语义不变。该修复不增加兼容入口、不复制任何业务实现，也不改变模块边界。

## 验证要求

修复已直接提交 `main`，但本轮尚未由用户本地重新执行 Closure Gate，因此不能提前记录 Gate 通过。必须在用户本地同步最新 `main` 后重新执行 Closure Gate，并继续执行全部既有重构 Gate 与 Backend Regression。
