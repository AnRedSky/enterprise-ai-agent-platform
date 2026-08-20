# 009 - Backend / Frontend 测试 Gate 违反隔离原则

## 实际错误

开发者执行 `backend/scripts/test/release/01_full_regression_gate.ps1` 时发现该脚本同时执行：

- `uv run pytest -q`
- Alembic migration/head verification
- Real HTTP API Gate
- `npm test`
- `npm run build`

该脚本因此把 Backend 与 Frontend 测试执行耦合在同一个测试脚本中。

## 根因

此前为了形成 Release / Full Regression 编排，错误地将 Backend regression、Migration、Real API 与 Frontend test/build 放进同一个 PowerShell 脚本。该设计与 `docs/DEVELOPMENT.md` 的“测试 Gate 严格隔离”及“Backend 测试脚本不得调用 npm、Frontend 测试独立执行”规则冲突。

## 影响

1. Backend Gate 失败会阻止 Frontend Gate 执行。
2. Frontend Gate 无法作为独立质量门单独执行。
3. Backend 测试脚本具有 Frontend 运行时依赖。
4. 测试失败来源无法通过脚本边界清晰区分。
5. Release / Full Regression 的单一编排入口与项目要求的 Backend / Frontend Gate 独立性冲突。

## 修复方案

直接在 `main` 修复：

1. 删除 `backend/scripts/test/release/01_full_regression_gate.ps1`。
2. 新增 `backend/scripts/test/release/01_backend_regression_gate.ps1`，仅执行 Backend regression → migration/head verification → Real API。
3. 新增 `backend/scripts/test/release/02_frontend_regression_gate.ps1`，仅执行 Frontend Vitest → production build。
4. 更新 `docs/DEVELOPMENT.md`，明确禁止任何单脚本同时执行 Backend 与 Frontend 测试。
5. 更新项目状态，移除“统一 Full Regression 编排”的错误规则。

## 预防措施

- Backend Gate 不得出现 `npm` 命令。
- Frontend Gate 不得出现 `uv`、Alembic、Real API 命令。
- Browser / Frontend-Backend E2E 后续作为第三个独立层实现。
- 测试脚本结构变更必须同时检查 `docs/DEVELOPMENT.md` 的 Gate 隔离规则。

## 验证要求

开发者本地必须分别执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

以及：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\02_frontend_regression_gate.ps1
```

必须实际检查两个脚本的执行范围：Backend Gate 不执行 npm；Frontend Gate 不执行 Backend 测试、Migration 或 Real API。未执行前不得标记通过。
