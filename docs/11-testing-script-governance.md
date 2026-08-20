# 测试脚本治理准则

## 1. Main 基线

所有开发、修复、测试脚本整改均以最新 `main` 为基线。不得为了测试目的创建临时开发分支；修正直接提交 `main`。

## 2. 测试层级与职责

```text
backend/tests/
├── unit/          # 单元测试
├── integration/   # Backend 内部集成测试
├── api_contract/  # FastAPI Contract / 认证边界 / 响应结构
└── api_real/      # 独立 Backend + 真实 HTTP
```

脚本只负责编排：

```text
scripts/test/regression/  # 默认项目回归
scripts/test/api-real/    # 唯一 Real API Gate
scripts/test/integration/ # 前后端联调 Gate
scripts/test/phase/       # 历史/阶段验收编排
```

Evaluation 与 Dev 不属于默认回归：

```text
scripts/evaluation/knowledge/
scripts/evaluation/embedding/
scripts/dev/
```

## 3. 固定 Gate 顺序

```text
Backend default regression
        ↓
Database migration/head
        ↓
Real HTTP API Gate（强制）
        ↓
Frontend test/build
        ↓
前后端联调
```

未通过 Real API Gate，不得进入前后端联调。

## 4. API 真实调用测试

真实 API 测试实现统一放在 `backend/tests/api_real/`；唯一编排入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

其中 `00_bootstrap_real_api.py` 只负责真实 HTTP 测试前置数据与认证上下文准备。Token、Workflow ID、Execution ID 必须自动取得，禁止要求开发人员手工填写。

## 5. 脚本职责

- `test/regression/`：默认项目回归。
- `test/api-real/`：真实 HTTP API。
- `test/integration/`：前后端联调 Gate。
- `test/phase/`：历史阶段验收编排。
- `migration/`：数据库迁移。
- `evaluation/knowledge/`：Knowledge/RAG 质量评估。
- `evaluation/embedding/`：Embedding Provider 专项评估。
- `dev/`：开发辅助与场景复现，不作为正式验收 Gate。

脚本只负责编排，不复制测试断言、登录逻辑、Token、Workflow/Execution Fixture 或公共数据库前置。

## 6. 防止冗余

新增 API 测试场景时：

1. 先检查 `tests/api_real/` 是否已有覆盖；
2. 优先扩展现有测试模块；
3. 只有职责完全不同才新增测试文件；
4. 不新增第二套认证/Fixture Bootstrap；
5. 不新增第二个 Real API Gate；
6. 联调 Gate 只能调用 canonical Real API Gate。

## 7. 根目录约束

`backend/tests` 根目录只允许 `README.md`、`conftest.py` 等测试基础设施文件，禁止 `test_*.py`。

`backend/scripts` 根目录只允许 `README.md`，禁止测试、业务、场景或验证脚本。
