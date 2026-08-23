# 2026-08-23 Backend 模块重构后的回归导入错误

## 1. 问题

完成 Agent、Knowledge 与 Provider 目录彻底迁移后，本地 Backend 全量测试出现 27 个 collection error，并且直接启动 FastAPI 也无法完成 import。

## 2. 根因

### 2.1 AgentService 类型注解与方法名冲突

`AgentService` 同时定义了 `list()` 方法，并在同一 class body 中使用 `list[AgentVersion]` 类型注解。Python 在定义后续方法时会优先解析 class namespace 中已经存在的 `list` 方法，因此把 `list` 解析成函数对象，导致：

```text
TypeError: 'function' object is not subscriptable
```

这属于目录重构后暴露出的既有 Python class-scope annotation 问题，并非业务行为变化。

### 2.2 测试与评估脚本仍引用已删除旧模块路径

彻底迁移明确删除了旧 Provider / Knowledge / Scheduler 路径，但部分测试和评估脚本仍引用旧入口，例如：

```text
app.services.vector_retrieval_provider
app.services.ollama_embedding_provider
app.services.knowledge_retrieval
app.services.scheduled_trigger_scheduler
```

这些引用违反“旧模块删除后禁止兼容垫片”的重构规则。

### 2.3 模块化 Gate PowerShell 引号兼容性问题

本地执行模块化 Gate 时出现 PowerShell parser error。虽然远端文件内容逻辑正确，但 Gate 脚本的单引号形式在实际 Windows PowerShell 执行环境中出现解析异常，因此改为统一使用双引号字符串，避免同类 parser failure。

## 3. 修复

- `AgentService` 增加 `from __future__ import annotations`，避免 class-scope 方法名遮蔽内建 `list` 的运行时注解解析；不改变任何业务接口或行为。
- Evaluation Vector Space 测试切换到 `app.infrastructure.providers.vector_retrieval`。
- Governed Embedding Profile smoke 切换到 `app.infrastructure.providers.ollama_embedding`。
- Knowledge retrieval baseline 切换到 `app.services.knowledge.retrieval`。
- Scheduled Trigger unit / recovery / Real API 测试切换到 `app.services.workflow_scheduler.runtime`，不新增旧路径兼容模块。
- Backend Module Refactor Gate 统一改用双引号字符串，保持原有 Gate 检查逻辑不变。

## 4. 业务影响

上述修复只恢复正确的模块导入和测试入口，不改变 Agent、Knowledge、Provider 或 Scheduled Trigger 的业务逻辑。

## 5. 验证要求

本错误记录只记录已分析和已提交的修复，不预填测试通过结果。必须在本地执行：

```powershell
cd backend
uv run pytest -q
```

以及：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

Real API 测试仍必须通过项目规定的独立 Real API Gate 执行，不能以默认 pytest collection 结果代替真实联调。
