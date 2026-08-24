"""模型 Provider API 领域包。

职责：暴露模型 Provider、Model Profile 与路由解析接口。
边界：不复制 Provider 技术适配；外部模型实现统一位于 infrastructure/providers。
关键依赖：FastAPI、ModelProviderService、模型 Schema 与数据库依赖。
"""
