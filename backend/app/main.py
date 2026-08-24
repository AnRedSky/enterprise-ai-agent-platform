import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.agents.chat import router as chat_router
from app.api.v1.agents.router import router as agents_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.knowledge.ingestion import router as knowledge_ingestion_router
from app.api.v1.knowledge.retrieval import router as knowledge_retrieval_router
from app.api.v1.knowledge.router import router as knowledge_router
from app.api.v1.model_providers.router import router as model_providers_router
from app.api.v1.organizations.router import router as organizations_router
from app.api.v1.runtime.router import router as runtime_router
from app.api.v1.tools.router import router as tools_router
from app.api.v1.usage.router import router as usage_router
from app.api.v1.webhooks.router import router as webhooks_router
from app.api.v1.workflows.executions import router as workflow_executions_router
from app.api.v1.workflows.router import router as workflows_router
from app.core.config import settings
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = ScheduledTriggerScheduler(settings.scheduler_poll_interval_seconds)
    task: asyncio.Task | None = None
    if settings.scheduler_enabled:
        task = asyncio.create_task(scheduler.run_forever(), name="scheduled-trigger-scheduler")
    app.state.scheduled_trigger_scheduler = scheduler
    try:
        yield
    finally:
        scheduler.stop()
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(chat_router, prefix="/api/v1/agents", tags=["chat"])
app.include_router(tools_router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(runtime_router)
app.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(knowledge_ingestion_router, prefix="/api/v1/knowledge", tags=["knowledge-ingestion"])
app.include_router(knowledge_retrieval_router, prefix="/api/v1/knowledge", tags=["knowledge-retrieval"])
app.include_router(model_providers_router, prefix="/api/v1/model-providers", tags=["model-providers"])
app.include_router(organizations_router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(usage_router, prefix="/api/v1/usage", tags=["usage"])
app.include_router(workflows_router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(workflow_executions_router, prefix="/api/v1/workflows", tags=["workflow-executions"])
app.include_router(webhooks_router, prefix="/api/v1/webhooks", tags=["webhooks"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "environment": settings.app_env}
