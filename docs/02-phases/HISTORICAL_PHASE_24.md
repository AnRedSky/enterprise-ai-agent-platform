# Historical Phase 24 — 历史规划与任务记录

> 仅保存旧连续编号体系的历史事实，不代表当前项目 Phase。当前状态以 `PROJECT_STATUS.md` 为准。

## 1. 进入背景

Phase 24 在 `40-phase-23-completion-and-phase-24-plan.md` 中作为 Phase 23 手工质量门禁之后的下一阶段提出。早期目标包括 P0 手工测试问题、CI 恢复、Tool Runtime、Memory、Observability、Vue Agent/Session/Debug 和最终 E2E。

## 2. 已核对任务

### Task 01 — pytest import / compatibility

`47-phase-24-task-01-backend-pytest-import-fix.md` 记录 Windows 环境 `pytest -q`、HTTP RBAC、RBAC Matrix 收集阶段统一 `ModuleNotFoundError: No module named 'app'`，17 个测试模块未进入执行。修复 `backend/tests/conftest.py` 显式加入 backend root 到 `sys.path`，不修改业务代码/断言。随后 `49-phase-24-task-01-backend-compatibility-fix.md` 又记录 10 个 collection errors：缺少 `app.core.config`、`app.api.dependencies`、`app.models.audit` 和错误 `HTTPRedirectHandler` 导入；新增/修复对应模块，并明确本地 `passlib` 未安装属于环境依赖，不能绕过。

### Task 02 — Runtime / Tool / Memory validation

`48` / `50` 规划要求在 collection 恢复后依次验证 Runtime API Contract、HTTP/Query RBAC、RBAC Matrix、Tool Runtime、安全/E2E、Memory Context/Governance/Service、Model Gateway、Observability；失败必须定位真实代码/配置/环境，禁止 skip/xfail/降低断言。

### uv 环境修复

`51-phase-24-task-02-uv-environment-fix.md` 记录将 `backend/pyproject.toml` 改为权威依赖声明并加入 dev dependencies、pytest `pythonpath/testpaths/asyncio_mode`；固定 `bcrypt==4.0.1`；CI 改为 `uv sync --dev` → compileall → pytest 并恢复 push/PR/workflow_dispatch；删除陈旧空项目 `uv.lock`，要求重新生成真实 lock。该记录明确当前环境无法访问 PyPI，因此不能虚构 `uv sync` / pytest 最终通过结果。

## 3. 历史状态规则

Phase 24 的这些文档主要是修复记录和验证规划；没有独立、完整的最终 Acceptance 文档证明全部 Runtime/Tool/Memory/Model Gateway/Observability 已关闭。因此本历史目录不把计划或修复提交等同于最终验收。

## 4. 历史来源

- `40-phase-23-completion-and-phase-24-plan.md`
- `47-phase-24-task-01-backend-pytest-import-fix.md`
- `48-phase-24-task-02-backend-runtime-tool-memory-validation-plan.md`
- `49-phase-24-task-01-backend-compatibility-fix.md`
- `50-phase-24-task-02-backend-runtime-validation-plan.md`
- `51-phase-24-task-02-uv-environment-fix.md`

## 5. 当前状态

Phase 24 保留为历史时间线；不覆盖当前项目 Phase 状态，也不继续使用旧连续编号创建新任务。