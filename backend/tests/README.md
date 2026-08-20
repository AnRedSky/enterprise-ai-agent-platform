# Backend 测试目录规范

## 1. 四层测试职责

```text
tests/
├── unit/          # 纯单元测试：Service / Model / Schema / Utility / 状态机
├── integration/   # Backend 内部集成：真实数据库/组件组合，不走浏览器
├── api_contract/  # API Contract：ASGI/TestClient，验证路由、Schema、认证边界
└── api_real/      # Real API：独立运行 Backend + 真实 HTTP 请求
```

- `unit/` 不依赖真实 HTTP 和真实外部服务，优先使用 Mock/Fixture。
- `integration/` 验证多个 Backend 组件的真实组合行为，可使用真实 PostgreSQL。
- `api_contract/` 不等价于真实部署验收；它验证 FastAPI Contract、认证边界和响应结构。
- `api_real/` 必须连接独立运行的 Backend 服务，通过 `httpx` 发起实际 HTTP 请求。

根目录禁止继续新增 `test_*.py`。历史根目录测试必须按实际测试行为迁移到四类目录之一；迁移后删除旧文件，禁止保留重复副本。

## 2. API Real Gate 是前后端联调前置条件

真实 API 测试必须在前后端联调之前完成。禁止手工填写 Token / Workflow ID / Execution ID；统一由 Real API bootstrap 自动准备。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

未通过 Real API Gate 时，禁止进入浏览器前后端联调。

## 3. 测试实现与脚本编排分离

```text
tests/        = 测试什么、断言什么
scripts/test/ = 如何编排执行
```

脚本不得复制测试断言、登录逻辑或 Workflow Fixture 逻辑；公共前置条件只维护一份。

## 4. 标准执行顺序

```text
Unit → Integration → API Contract → Real API → Frontend Test/Build → Frontend/Backend 联调
```

`pytest -q` 只能代表本地 Python 测试通过，不能替代 Real API Gate。
