"""数据库基础设施：提供应用唯一的 SQLAlchemy Engine、Session 与请求会话生成器。

边界：只负责数据库连接生命周期与 Session 创建，不承载业务 Repository 或领域规则。
关键依赖：SQLAlchemy AsyncEngine 与项目数据库配置。
"""

from app.infrastructure.db.session import SessionLocal, engine, get_db_session

__all__ = ["SessionLocal", "engine", "get_db_session"]
