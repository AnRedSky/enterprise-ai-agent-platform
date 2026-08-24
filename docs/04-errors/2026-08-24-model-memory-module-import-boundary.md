# Model / Memory 模块迁移后的旧入口残留

- 发现时间：2026-08-24
- 发现阶段：Backend 模块化整改，Model 迁移完成后的本地导入验证
- 影响范围：Backend 应用启动导入、模块重构 Gate

## 现象

Model 迁移完成后，`app/services/usage_accounting.py` 仍引用已删除的 `app.services.model_provider_governance_contract`，导致：

```text
ModuleNotFoundError: No module named 'app.services.model_provider_governance_contract'
```

同时，Memory 单元测试仍引用已经删除的 `app.services.memory_service`，导致模块重构 Gate 将该测试识别为旧路径残留。

## 根因

本轮领域物理迁移只切换了已识别的生产入口，但遗漏了一个跨领域 Service 对 Model Contract 的引用，以及一个测试模块对旧 Memory Service 文件路径的引用。该问题说明领域迁移不能只验证目标模块自身，必须同时检查全仓生产代码与测试代码的旧 import。

## 修复

1. 将 `UsageAccountingService` 的 `CostUnit`、`PricingSource` import 切换到 `app.services.model.contract`。
2. 将 `tests/unit/test_memory_governance.py` 切换到 `app.services.memory` 正式入口。
3. 为 Memory 治理测试补充中文模块职责、边界和关键依赖说明。
4. 未新增兼容垫片、代理文件或第二套实现。

## 验证要求

开发者本地必须重新执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q tests/unit/test_model_gateway.py tests/unit/test_model_provider_governance_contract.py tests/unit/test_runtime_model_governance.py tests/unit/test_memory_governance.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
uv run pytest -q
```

本记录不预填测试通过结论；最终结果以开发者本地实际执行输出为准。
