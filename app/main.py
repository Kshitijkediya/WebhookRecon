from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import reconciliation, webhooks
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="WebhookRecon",
    description="Webhook Reconciliation Engine with Autonomous Ledger Healing",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = (
    ["*"] if settings.app_env == "development"
    else settings.cors_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(reconciliation.router, prefix="/reconcile", tags=["reconciliation"])


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
