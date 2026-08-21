# API 测试与本地手工验收

## 1. 自动化 API Contract

Backend API pytest 按模块覆盖 health、auth、agents、chat、runtime、tools；完整回归使用 `uv run pytest -q`。API Contract 与真实 HTTP 不混淆：TestClient/ASGITransport 只证明 Contract，真实 HTTP 必须进入 `tests/api_real/` 和 canonical Real API Gate。

## 2. 真实 API 场景

历史 API 场景固定顺序：

```text
Health → Auth → Agents → Chat/SSE → Runtime → Tools
```

`backend/scripts/run_api_scenario.ps1` 会自动注册/登录测试用户、创建 Agent、验证版本、Chat SSE start/done、Runtime executions/detail/events/audit、Tools 查询和未知 Tool 保护路径。

当前正式 Real API Gate 入口由 `01-governance/DEVELOPMENT.md` 和 `LOCAL_TESTING.md` 定义，历史 `run_api_scenario.ps1` 只作为早期手工场景记录。

## 3. 本地基础服务

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run pytest -q
uv run uvicorn app.main:app --reload
```

Frontend：

```powershell
cd frontend
npm ci
npm test
npm run build
```

## 4. 手工反馈

必须记录：工作目录、前置条件、实际命令、实际输出、失败 traceback / HTTP response、是否修改环境配置。禁止预填 PASS，禁止提交密码/API Key/JWT 完整 Token。

## 5. 历史来源

- `API_SCENARIO_SMOKE_TEST.md`
- `API_UNIT_TESTING.md`
- `11-manual-test-scenarios.md`
- `11-testing-script-governance.md`
- `14-development-command-reference.md`
