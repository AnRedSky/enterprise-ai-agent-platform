"""Scheduler Service 独立启动脚本。

职责：提供开发者和部署系统统一的 Scheduler Service 进程入口。
边界：不启动 FastAPI、不注册 HTTP 路由；API Service 使用 `run.py` 独立启动。
"""

from app.entrypoints.scheduler import main


if __name__ == "__main__":
    main()
