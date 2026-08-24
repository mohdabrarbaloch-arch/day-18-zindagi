"""Zindagi — Blood Donor Network. FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.core.compatibility import (
    BLOOD_GROUPS,
    CAN_DONATE_TO,
    UNIVERSAL_DONOR,
    UNIVERSAL_RECIPIENT,
)
from app.database import Base, engine
from app.routers import admin, auth, donors, requests

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A blood donor network that matches compatible donors to emergency requests.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(donors.router)
app.include_router(requests.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/api/blood-groups")
def blood_groups():
    """Public reference: compatible donor groups per patient group."""
    return {
        "groups": BLOOD_GROUPS,
        "universal_donor": UNIVERSAL_DONOR,
        "universal_recipient": UNIVERSAL_RECIPIENT,
        "compatibility": {patient: sorted(donors) for patient, donors in CAN_DONATE_TO.items()},
    }


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str):
    """Serve the SPA for any non-API route."""
    return FileResponse("static/index.html")
