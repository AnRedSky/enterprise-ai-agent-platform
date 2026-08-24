"""Organization API 领域包。

职责：暴露组织、成员及组织治理相关 HTTP 接口。
边界：不实现成员权限和租户治理规则；业务统一由 OrganizationService 负责。
关键依赖：FastAPI、OrganizationService、组织 Schema 与数据库依赖。
"""
