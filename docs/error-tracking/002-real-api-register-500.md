# 002 Real API 注册接口 500

## 现象

Phase 1.5-F Real API Gate 在准备测试上下文时，随机创建测试用户并调用 `POST /api/v1/auth/register`，开发者本地反馈返回 `500 Internal Server Error`；同一轮 Backend 单元/集成/API Contract 回归仍通过。

## 判断

注册接口原先只做了用户名存在性预检查。并发注册或旧本地数据库中的 tenant / role 数据约束冲突仍可能在 `flush()` / `commit()` 阶段直接冒泡为 500。

当前修复在注册事务边界捕获 `sqlalchemy.exc.IntegrityError`，执行 rollback，并将数据库完整性冲突转换为明确的 HTTP 409；正常路径保持原有 self-healing tenant / role 初始化逻辑不变。

这不能替代对真实 PostgreSQL 环境的最终验证，因此修复后必须重新执行 Real API Gate，并在失败时结合后端服务日志继续定位非完整性约束类异常。

## 验收顺序

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

前端继续执行既有测试链，不新增测试入口。
