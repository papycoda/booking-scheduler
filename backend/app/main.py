from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.errors import register_exception_handlers
from app.middleware.rate_limiter import limiter
from app.routers.availability import router as availability_router
from app.routers.auth import router as auth_router
from app.routers.bookings import router as bookings_router
from app.routers.public import router as public_router
from app.routers.services import router as services_router
from app.routers.staff import router as staff_router
from app.routers.tenants import router as tenants_router
from app.routers.webhooks import router as webhooks_router
from app.services.reminder_scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="Booking Scheduler API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

allowed_origins = [str(settings.frontend_url).rstrip("/")]
if settings.environment == "development":
    allowed_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(staff_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount(settings.upload_base_url, StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
