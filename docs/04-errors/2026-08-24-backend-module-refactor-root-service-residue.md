# Backend 模块重构根服务残留与模块说明 Gate 阻塞

## 1. 错误现象

本轮 `main` 在完成剩余根目录 Service 物理迁移后，开发者本地验证出现两类阻塞：

1. `uv run python -c "from app.main import app; print('APP_IMPORT_OK')"` 在 `app/api/chat.py` 继续引用已删除的 `app.services.observability_service` 时失败。
2. Module Refactor Gate 在 `app/services/agent/__init__.py` 处报告缺少模块职责与边界说明。

## 2. 根因

- Observability 已迁移至 `app.services.observability`，但 Chat API 未完成 canonical import 切换。
- Agent 模块入口只有简短入口说明，没有按开发准则要求明确 `职责：` 与 `边界：`。
- 本轮重构采用物理删除旧模块的策略，因此不能通过兼容垫片恢复旧 import。

## 3. 修复原则

- Chat API 直接引用 `app.services.observability.ObservabilityService` 正式入口。
- Agent `__init__.py`、Service、Repository 补充中文职责与边界说明，并明确不重复实现其他领域能力。
- 不恢复旧模块文件、不增加旧入口转发、不复制第二套实现。
- 本错误记录只记录已分析的工程阻塞，不把尚未执行的本地测试写成通过。

## 4. 本轮修复

- 修复 `backend/app/api/chat.py` 的 Observability canonical import。
- 完善 `backend/app/services/agent/` 三个模块文件的职责与边界说明。

## 5. 验证要求

必须在开发者本地重新执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
uv run pytest -q
```

在上述命令实际执行前，不记录 Gate 或 Backend Regression 已通过。
