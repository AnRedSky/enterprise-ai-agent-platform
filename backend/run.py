"""API Service 独立启动脚本。

职责：启动 FastAPI API Service。
边界：不启动 Scheduler；Scheduler 必须通过 `run_scheduler.py` 作为独立进程运行。
"""

import uvicorn

from app.core.config import settings


def print_startup_info() -> None:
    """打印 API Service 启动所需的关键运行信息。

    不打印数据库连接串、JWT Secret、模型 API Key 等敏感配置。
    """
    reload_enabled = settings.app_env == "development"
    print("=" * 64, flush=True)
    print("Enterprise AI Agent Platform - API Service", flush=True)
    print("=" * 64, flush=True)
    print(f"Service       : api", flush=True)
    print(f"Environment   : {settings.app_env}", flush=True)
    print(f"Bind Address  : http://{settings.app_host}:{settings.app_port}", flush=True)
    print(f"API Base      : http://{settings.app_host}:{settings.app_port}/api/v1", flush=True)
    print(f"Health Check  : http://{settings.app_host}:{settings.app_port}/health", flush=True)
    print(f"Reload        : {'enabled' if reload_enabled else 'disabled'}", flush=True)
    print("Scheduler     : external service (run_scheduler.py)", flush=True)
    print("=" * 64, flush=True)


if __name__ == "__main__":
    print_startup_info()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
