"""API 协议适配层。

职责：承载 HTTP 路由与版本化 API 包，不实现领域业务规则。
边界：业务逻辑必须下沉到 Service / Runtime；数据库访问通过 Dependencies 与领域服务完成。
关键依赖：FastAPI 及各领域 Service / Schema Contract。
"""
