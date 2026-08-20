# 开发准则

## 1. Main 基线与分支

1. 所有开发工作以最新 `main` 为唯一基线。
2. 开始任务前必须同步最新 `main`，确认本地工作区基于最新提交。
3. **禁止创建任何开发分支、临时分支或任务分支**；修改直接在 `main` 上推进。
4. 不得基于过期提交继续开发；发现远端 `main` 已更新时，应先同步后再修改。

## 2. Backend 测试分层与目录职责

Backend 测试严格分为四层：

- `backend/tests/unit/`：纯单元测试，验证 Service / Model / Schema / Utility / 状态机等内部行为。
- `backend/tests/integration/`：Backend 内部集成测试，验证多个组件与真实数据库/基础设施的组合行为。
- `backend/tests/api_contract/`：API Contract 测试，验证路由、Method、Schema、认证/权限边界；允许 TestClient / ASGITransport，不代表真实网络调用。
- `backend/tests/api_real/`：真实 HTTP API 测试，必须连接独立运行的 Backend 服务，不得使用 TestClient / ASGITransport 代替真实 HTTP。

`backend/tests/` 根目录禁止新增 `test_*.py`。历史测试必须按实际行为迁移到四层之一；迁移后删除旧文件，禁止重复副本。

## 3. Scripts 与 Tests 严格分离

- `backend/tests/` 只保存测试实现与断言。
- `backend/scripts/test/api-real/` 负责 Real API 的自动化前置条件与统一编排。
- `backend/scripts/test/integration/` 负责前后端自动化联调 Gate，只调用已有测试入口，不复制测试逻辑。
- `backend/scripts/test/regression/` 负责阶段性完整回归编排。
- `backend/scripts/migration/` 只负责数据库迁移。
- `backend/scripts/evaluation/knowledge/`、`embedding/` 只负责质量评估/专项验证，不作为普通 pytest 测试目录。
- `backend/scripts/dev/` 仅保存开发辅助脚本，不作为正式验收 Gate。

`backend/scripts/` 根目录禁止新增脚本。旧脚本必须迁移后删除原入口，并同步更新调用文档。

## 4. 前后端联调强制顺序

前后端联调前，必须完成真实 API 自动化测试，顺序固定为：

1. Backend 全量回归：`uv run pytest -q`。
2. 数据库迁移：`uv run alembic upgrade head`，并执行 `uv run alembic current` 验证 head。
3. **真实 HTTP API 自动化测试**：`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1`。
4. Real API 全部通过后，才允许进入 Frontend / Backend 联调。
5. 前端自动化回归：`npm test`、`npm run build`。
6. 最后进行浏览器级前后端联调，并记录实际验收结果。

统一联调入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

任何 Real API 测试失败，都必须阻断前后端联调，不允许手工绕过失败项。

## 5. Real API 测试前置条件必须自动生成

禁止要求开发人员手工填写：

```powershell
$env:ACCESS_TOKEN="<real token>"
$env:WORKFLOW_ID="<workflow id>"
$env:WORKFLOW_EXECUTION_ID="<execution id>"
```

统一由 `00_bootstrap_real_api.py` 通过真实 HTTP 注册/登录并自动发现或创建测试 Workflow、Execution，测试结束后清理临时 context。

## 6. 错误跟踪

发现异常时必须记录到 `docs/error-tracking/`，至少包含发生阶段、命令、错误摘要、根因、修复方案、验证结果、防重复措施。

## 7. 文档职责分离

- 开发准则：`docs/DEVELOPMENT_GUIDELINES.md`，只维护长期有效规则。
- 任务进度：`docs/PROJECT_STATUS.md` 与 Phase 文档，维护阶段状态和验收结果。
- 错误记录：`docs/error-tracking/`，维护历史异常及防重复措施。

三类内容不得混写。
