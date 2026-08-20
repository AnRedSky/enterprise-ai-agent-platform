# 开发准则

## 1. Main 基线与分支

1. 所有开发工作以最新 `main` 为唯一基线。
2. 开始任务前必须同步最新 `main`，确认本地工作区基于最新提交。
3. **禁止创建任何开发分支、临时分支或任务分支**；修改直接在 `main` 上推进。
4. 不得基于过期提交继续开发；发现远端 `main` 已更新时，应先同步后再修改。

## 2. 测试分层

Backend 测试必须明确区分：

- `backend/tests/`：单元测试及后端内部 Contract 测试。
- `backend/tests/api_contract/`：API 路由、认证和 Contract 层测试；允许使用 FastAPI TestClient / ASGITransport，不代表真实网络调用。
- `backend/tests/api_real/`：真实 HTTP API 测试；必须连接已经启动的 Backend 服务，不得 import `app.main` 作为被测服务，也不得使用 TestClient / ASGITransport 代替真实 HTTP。

新增 API 测试必须按照上述目录归类，不得将真实 API 测试混入单元测试。

## 3. 前后端联调强制顺序

前后端联调前，必须先完成真实 API 自动化测试，顺序固定为：

1. Backend 单元 / Contract 全量回归：`uv run pytest -q`。
2. 数据库迁移：`uv run alembic upgrade head`，并执行 `uv run alembic current` 验证 head。
3. **真实 HTTP API 自动化测试**：`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_real_validation.ps1`。
4. 真实 API 测试全部通过后，才允许进入 Frontend / Backend 联调。
5. 前端自动化回归：`npm test`、`npm run build`。
6. 最后进行浏览器级前后端联调，并记录实际验收结果。

任何真实 API 测试失败，都必须阻断前后端联调，不允许通过手工绕过失败项继续验收。

## 4. 统一自动化入口

标准联调门禁使用：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_frontend_backend_integration_gate.ps1
```

该入口强制执行 Backend regression、migration head、真实 HTTP API、Frontend test/build 的顺序。

## 5. API 测试真实性要求

“API 测试通过”必须区分以下两种结果：

- API Contract 通过：证明应用路由、依赖和认证 Contract 正确。
- Real API 通过：证明已经启动的实际 Backend 服务能够通过 HTTP 正常提供接口。

只有 Real API 通过，才允许宣称“前后端联调前 API 已验收”。

## 6. 错误跟踪

发现异常时必须记录到 `docs/error-tracking/` 独立错误跟踪目录，至少包含：

- 发生阶段
- 执行命令
- 完整错误摘要
- 根因
- 修复方案
- 验证结果
- 防重复措施

错误解决后不得只修改代码而不记录可复用的错误经验。

## 7. 文档职责分离

- 开发准则：`docs/DEVELOPMENT_GUIDELINES.md`，只维护长期有效的开发规则。
- 任务进度：`docs/PROJECT_STATUS.md` 及各 Phase 文档，维护阶段状态和验收结果。
- 错误记录：`docs/error-tracking/`，维护历史异常及防重复措施。

三类内容不得混写，以便后续独立维护和审计。
