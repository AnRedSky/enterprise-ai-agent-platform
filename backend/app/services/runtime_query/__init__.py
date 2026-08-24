"""Runtime Query 查询服务。

职责：提供执行、事件、审计日志和 Workflow Trace 的分页查询与权限范围控制。
边界：只负责查询与访问范围，不负责执行编排、写入审计或创建数据库 Session。
"""

from .service import RuntimeQueryService

__all__ = ["RuntimeQueryService"]
