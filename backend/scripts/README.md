# Backend scripts 目录规范

`backend/scripts` 只保存可重复执行的工程脚本，按**用途**分类，不按业务代码堆放。

## 目录职责

```text
scripts/
├── test/
│   ├── api-real/       # Real API 自动化测试唯一编排入口
│   ├── integration/    # 前后端联调 Gate
│   └── regression/     # 项目阶段性完整回归入口
├── migration/          # Alembic 数据库迁移
├── evaluation/
│   ├── knowledge/      # Knowledge/RAG 质量评估
│   └── embedding/      # Embedding Provider 专项评估
└── dev/                # 开发辅助脚本，不作为正式验收 Gate
```

数字前缀只表示同一目录内的执行顺序，不代表 Phase 编号。

## 三类测试严格隔离

```text
tests/                  = 测试实现与断言
scripts/test/regression = 默认项目回归编排
scripts/test/api-real   = 独立真实 HTTP API Gate
scripts/test/integration= 前后端联调 Gate
```

### 1. 默认回归

`uv run pytest -q` **只运行本地单元/契约/组件测试，默认排除 `real_api`**。这是开发期间和提交前的基础回归，不要求后端 HTTP 服务运行，也不要求 Token、Workflow ID 或 Execution ID。

对应脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\regression\01_backend_regression.ps1
```

### 2. Real API

真实 API 测试必须显式执行，不允许进入默认 `pytest` 回归。唯一入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

该入口先运行 `00_bootstrap_real_api.py`，自动完成真实 HTTP 注册/登录、Workflow/Execution 准备，并临时注入 `ACCESS_TOKEN`、`WORKFLOW_ID`、`WORKFLOW_EXECUTION_ID`。测试结束后自动清理上下文；开发人员禁止手工填写这些变量。

Real API Gate 未通过时，不允许进入前后端联调。

### 3. 前后端联调

联调 Gate 是三类测试之间的唯一顺序编排入口，固定顺序：

```text
① Backend default regression
        ↓
② Database migration/head verification
        ↓
③ Real API Gate
        ↓
④ Frontend test + production build
        ↓
⑤ 浏览器/人工业务场景联调
```

执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

该脚本只负责调用既有 Gate，不复制 Token、登录、Workflow Fixture、API 断言或前端测试逻辑。任一前置 Gate 失败立即停止。

## 唯一测试编排原则

禁止在多个脚本中复制登录、Token、Workflow Fixture、API 断言或同一数据库前置逻辑。测试实现只能归属 `backend/tests`；脚本只负责编排和 Gate。

## Migration / Evaluation

Evaluation 是质量评估程序，不是 pytest 单元测试；Migration 只负责数据库迁移。二者不得混入测试目录，也不参与默认 pytest 回归。

## 迁移规则

根目录历史脚本属于待治理遗留项。新增脚本禁止放在 `backend/scripts` 根目录；迁移完成后删除旧入口，并同步修正文档中的调用路径。
