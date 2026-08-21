# Backend scripts 目录规范

`backend/scripts` 只保存可重复执行的工程脚本，按**用途**分类，不按业务代码堆放。

## 目录职责

```text
scripts/
├── test/
│   ├── api-real/      # Real API 自动化测试唯一编排入口
│   ├── release/       # Backend Release / Regression Gate
│   ├── integration/   # 未来真正 Frontend/Backend 联调编排
│   └── phase/         # 历史/阶段性验收编排，按 Phase 子目录归档
├── migration/         # Alembic 数据库迁移
├── evaluation/
│   ├── knowledge/     # Knowledge/RAG 质量评估与专项验证
│   └── embedding/     # Embedding Provider 专项评估
└── dev/               # 开发辅助、场景复现、本地环境检查；不是正式验收 Gate
```

数字前缀只表示同一目录内的执行顺序，不代表 Phase 编号。

## 测试实现与 Gate 严格隔离

```text
tests/                   = 测试实现与断言
scripts/test/api-real    = 独立真实 HTTP API Gate
scripts/test/release     = Backend Release / Regression Gate
scripts/test/integration = 未来 Frontend/Backend 联调编排
scripts/test/phase       = 历史/阶段验收编排
```

### 1. 默认回归

开发期间默认回归直接执行：

```powershell
uv run pytest -q
```

它运行本地 unit / integration / API contract 测试并默认排除 `real_api`，不要求后端 HTTP 服务、Token 或 Workflow ID。

Backend Release Gate 会将默认回归、Migration 和 Real API 按固定顺序串联：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

### 2. Real API

真实 API 测试唯一入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

该入口先运行 `00_bootstrap_real_api.py`，自动完成真实 HTTP 注册/登录及所需 Workflow/Execution fixture 准备，并临时注入相关环境变量。开发人员禁止手工填写这些变量。

Real API Gate 未通过时，不允许进入前后端联调。

### 3. Frontend / Backend Integration

`test/integration/` 只保留未来真正的 Frontend / Backend 联调编排职责，不复制 Backend regression、Migration、Real API 或 Frontend regression。

Browser / Frontend-Backend E2E 由 `frontend/scripts/test/e2e/` 独立管理。

### 4. Phase 阶段验收

`test/phase/<phase>/` 仅用于历史阶段验收和开发阶段检查的归档。它不是默认回归入口，也不是 Real API 或 Release Gate 入口。新阶段完成后，应优先把稳定断言沉淀到 `tests/` 四层体系，阶段脚本只保留必要的编排。

## 唯一测试编排原则

禁止在多个脚本中复制登录、Token、Workflow Fixture、API 断言或同一数据库前置逻辑。测试实现只能归属 `backend/tests`；脚本只负责编排和 Gate。

## Migration / Evaluation / Dev

Migration 只负责数据库迁移；Evaluation 是质量评估程序；Dev 是本地开发辅助。三者均不得混入默认 pytest 回归，也不得伪装成 Real API 或 Release Gate。

## 迁移规则

`backend/tests` 根目录禁止 `test_*.py`；`backend/scripts` 根目录禁止业务/测试脚本，只允许 README。历史根目录文件必须迁移到职责明确的目录后删除旧入口；新增脚本禁止放在两个根目录。
