"""Knowledge API 领域包。

职责：组织知识库、文档及知识版本管理接口。
边界：不实现知识注册、摄取、检索和向量索引业务；这些职责统一由 Knowledge Service 承担。
关键依赖：FastAPI、Knowledge Service、Knowledge Schema 与数据库依赖。
"""
