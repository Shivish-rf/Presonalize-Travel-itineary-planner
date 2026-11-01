from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, destinations, itineraries, trips
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(destinations.router, prefix=settings.api_prefix)
app.include_router(itineraries.router, prefix=settings.api_prefix)
app.include_router(trips.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["health"], summary="Health check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
