# 002 Backend / Frontend 测试 Gate 跨栈耦合

## 发生阶段

Phase 1.5 Workflow / Governance 工程治理整改阶段。

## 实际错误

曾存在 `Full Regression Gate` 同时编排 Backend 与 Frontend 测试的情况，导致 Backend 测试脚本能够调用 Frontend 的 `npm test` / `npm run build`。这与项目开发准则要求的前后端测试完全独立相冲突。

## 根因

早期将“全量回归”理解为单脚本串联所有技术栈测试，而不是按照技术栈、运行时、依赖和失败边界拆分质量 Gate。

## 影响

1. Backend 与 Frontend 的失败责任边界不清晰。
2. Backend Gate 依赖 Node/npm 环境，违反 Backend 独立运行要求。
3. Frontend Gate 可能反向依赖 Python/uv 环境。
4. 测试脚本目录职责被混淆，后续维护容易再次产生跨栈耦合。

## 修复方案

已将 Gate 拆分为：

```text
Backend
backend/scripts/test/release/01_backend_regression_gate.ps1
backend/scripts/test/api-real/01_run_real_api_tests.ps1

Frontend
frontend/scripts/test/release/01_frontend_regression_gate.ps1
```

Backend Gate 只执行 Backend pytest、Migration/head 和 Real API；Frontend Gate 只执行 Frontend Vitest 与 production build。

Browser / Frontend-Backend E2E 若未来实现，必须作为第三独立层，不得恢复为 Full Regression Gate。

## 预防措施

1. `DEVELOPMENT.md` 明确禁止 Backend 调用 npm、Frontend 调用 uv/pytest/Alembic/Real API。
2. 测试脚本必须位于所属技术栈项目目录。
3. 不再创建跨前后端的 Full Regression Gate。
4. 每次测试治理变更必须检查脚本目录、工作目录、依赖和失败状态是否独立。

## 验证要求

- 静态检查 Backend / Frontend release script 不存在跨栈命令调用。
- 分别从 `backend/` 与 `frontend/` 启动各自 Gate。
- 后续新增 E2E 时必须建立独立 Gate，而不是修改 Backend / Frontend Gate。

## 实际验证结果

本记录不预填未执行的验证结果。最终实际测试结果应记录在对应 `PROJECT_STATUS.md` / Phase 文档中。
