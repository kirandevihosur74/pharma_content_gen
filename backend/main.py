import os
import time
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
import llm

from routers import health, assets, session, chat, messages, claims, content, versions, ingest

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from ingestion import ingest_approved_assets
    result = ingest_approved_assets()
    logger.info("Asset ingestion: %d ingested, %d updated", result["ingested"], result["updated"])
    logger.info("LLM integration: ENABLED (Anthropic Claude)")
    yield


app = FastAPI(title="FRUZAQLA Marketing Content Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.environ.get("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info(">>> %s %s", request.method, request.url.path)
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "<<< %s %s -> %d (%.1fms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


# Register routers
app.include_router(health.router)
app.include_router(assets.router)
app.include_router(session.router)
app.include_router(chat.router)
app.include_router(messages.router)
app.include_router(claims.router)
app.include_router(content.router)
app.include_router(versions.router)
app.include_router(ingest.router)
