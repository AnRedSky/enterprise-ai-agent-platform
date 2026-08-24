"""认证 API 领域包。

职责：暴露注册、登录等认证 HTTP 接口。
边界：不实现密码、Token 或角色业务规则；相关能力由 core 安全组件负责。
关键依赖：FastAPI、app.core.security、用户 ORM 与数据库依赖。
"""
