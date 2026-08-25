"""API Service 独立启动脚本。

职责：启动 FastAPI API Service。
边界：不启动 Scheduler；Scheduler 必须通过 `run_scheduler.py` 作为独立进程运行。
"""

import uvicorn

from app.core.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
