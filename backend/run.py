import uvicorn

from app.core.config import settings

# uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
