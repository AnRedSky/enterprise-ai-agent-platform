"""v1 API 版本包。

职责：统一承载当前稳定的 `/api/v1` HTTP 领域路由。
边界：只组织 API 版本与领域边界，不复制业务实现。
关键依赖：FastAPI Router、领域 Service 与 Schema Contract。
"""
