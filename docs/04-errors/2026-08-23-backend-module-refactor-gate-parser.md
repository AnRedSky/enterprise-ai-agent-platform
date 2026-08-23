# 2026-08-23 Backend Module Refactor Gate PowerShell Parser Error

## 现象

开发者在 `main` 基线本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

PowerShell 在脚本末尾报告：

```text
The string is missing the terminator: "
FullyQualifiedErrorId : TerminatorExpectedAtEndOfString
```

## 分析

远端脚本内容与预期的 PowerShell 字符串结构一致，但本地执行仍在末尾 `Write-Host` 行触发解析错误，说明该 Gate 对脚本编码/字符串解析环境过于敏感。该问题与 Backend Python 模块本身无关，但会阻断模块化整改 Gate。

## 修复

将 Gate 的固定字符串统一改为单引号，移除末尾中文输出字符串，并启用 `Set-StrictMode -Version Latest`。中文说明保留在注释中，避免 PowerShell 在本地脚本编码差异下把非 ASCII 文本参与字符串解析。

同时保留原有旧路径、重复实现、Provider 目录以及 targeted tests / Backend Regression 检查，不改变 Gate 的业务验收语义。

## 验证要求

修复后必须在开发者本地重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

只有本地实际执行成功后，才允许在项目状态中记录该 Gate Passed。
