# ERR-0004 — Real API 注册接口 500

- Legacy ID: `002-real-api-register-500`
- Phase: 1.5-F
- 类型: Real API / Transaction

## 现象
Real API bootstrap 调用 `POST /api/v1/auth/register` 曾返回 500，而单元/集成/API Contract 回归通过。

## 根因
用户名存在性预检查无法覆盖并发注册或旧数据库 tenant/role 完整性约束；IntegrityError 在 commit 阶段直接冒泡。

## 修复
注册事务捕获 `sqlalchemy.exc.IntegrityError`、rollback，并转换为 HTTP 409；正常 self-healing tenant/role 初始化保持不变。

## 验证
必须重新执行 Backend pytest、migration 和 Real API Gate，真实 PostgreSQL 结果为准。
