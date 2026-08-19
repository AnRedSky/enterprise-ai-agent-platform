from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.agents import router as agents_router
from app.api.runtime import router as runtime_router
from app.api.tools import router as tools_router
from app.api.knowledge import router as knowledge_router
from app.api.knowledge_ingestion import router as knowledge_ingestion_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(chat_router, prefix="/api/v1/agents", tags=["chat"])
app.include_router(tools_router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(runtime_router)
app.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(knowledge_ingestion_router, prefix="/api/v1/knowledge", tags=["knowledge-ingestion"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "environment": settings.app_env}
