"""Scheduler Service 独立启动脚本。

职责：提供开发者和部署系统统一的 Scheduler Service 进程入口。
边界：不启动 FastAPI、不注册 HTTP 路由；API Service 使用 `run.py` 独立启动。
"""

from app.core.config import settings
from app.entrypoints.scheduler import main


def print_startup_info() -> None:
    """打印 Scheduler Service 启动所需的关键运行信息。

    Scheduler Service 的身份由本启动脚本确定，不通过配置开关与 API Service 二选一。
    不打印数据库连接串、JWT Secret、模型 API Key 等敏感配置。
    """
    print("=" * 64, flush=True)
    print("Enterprise AI Agent Platform - Scheduler Service", flush=True)
    print("=" * 64, flush=True)
    print("Service       : scheduler", flush=True)
    print(f"Environment   : {settings.app_env}", flush=True)
    print("Transport     : PostgreSQL durable scheduler state", flush=True)
    print(f"Poll Interval : {settings.scheduler_poll_interval_seconds}s", flush=True)
    print("HTTP API      : none (independent background service)", flush=True)
    print("API Service   : run.py (independent process)", flush=True)
    print("=" * 64, flush=True)


if __name__ == "__main__":
    print_startup_info()
    main()
