# Phase 2.9 PostgreSQL Real Gate PowerShell 解析失败

## 1. 问题

开发者在 Windows PowerShell 执行 `backend/scripts/test/phase-2.9/01_reliable_delivery_postgres_gate.ps1` 时出现 ParserError，错误位置集中在 `.env` 路径字符串附近，并进一步产生缺失引号、括号和代码块的连锁解析错误。

## 2. 根因

Gate 脚本使用 UTF-8 无 BOM 文本保存，同时包含中文自然语言字符串。Windows PowerShell 5.1 对无 BOM UTF-8 脚本的编码识别依赖系统代码页；当本地环境以非 UTF-8 代码页解析脚本时，非 ASCII 字节会产生乱码并可能破坏字符串解析，从而把后续正常的 PowerShell 语法误报为缺失引号、括号或代码块。

该问题不是 `.env` 路径本身的语法问题，也不是 Alembic、pytest 或 PostgreSQL 问题。

## 3. 修复

`01_reliable_delivery_postgres_gate.ps1` 已重新保存为带 UTF-8 BOM 的 PowerShell 脚本，并移除 Gate 输出中的非 ASCII 文本，使 Windows PowerShell 5.1 与 PowerShell 7 均可稳定解析。

同时保持既有测试边界：

- Gate 不自动启动或停止 API、Worker、Scheduler、Redis、PostgreSQL；
- 测试数据继续由 pytest 自动生成；
- 不要求开发者手工填写 tenant、event、idempotency key 或其他测试信息；
- Gate 仍只负责 Migration/head、Real PostgreSQL delivery 验收和定向 Unit Regression 编排。

## 4. 验证要求

修复提交后必须在 Windows 本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\01_reliable_delivery_postgres_gate.ps1
```

必须首先确认脚本通过 PowerShell 解析阶段，再观察 Migration、Real PostgreSQL 和 Unit Regression 的实际结果。不得将未实际执行的结果记录为通过。

## 5. 边界

本修复只解决 Gate 脚本在 Windows PowerShell 下的可解析性，不改变 Reliable Delivery 生产代码、数据库模型、租约语义或 Real API 验收逻辑。
