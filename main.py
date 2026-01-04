from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import asyncio
import os

from app.api.routes import user, auth, family_member, family_activity ,family_document, announcement, shared_document,family,prayer_chain, timestamp_analytics, chat, websocket, analytics, recommendation, feedback, config, dashboard, public_checkin, public_qr, family_role, bcc
from app.api.endpoints import system_logs
from app.core.logging_middleware import LoggingMiddleware
from dotenv import load_dotenv

from app.db.init_db import init_db
from app.core.websocket_manager import start_cleanup_task
from app.core.logging_config import setup_logging

load_dotenv()

# Setup logging configuration
setup_logging()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()
    # Start WebSocket cleanup task
    asyncio.create_task(start_cleanup_task())

from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(family.router, prefix="/families", tags=["Families"])
app.include_router(family_member.router, prefix="/family/family-members", tags=["Family Members"])
app.include_router(family_activity.router, prefix="/family/family-activities", tags=["Activities"])
app.include_router(family_document.router, prefix="/family/family-documents", tags=["Documents"])
app.include_router(announcement.router, prefix="/announcements", tags=["Announcements"])
app.include_router(shared_document.router, prefix="/shared-documents", tags=["Shared Documents"])
app.include_router(prayer_chain.router, prefix="/prayer-chains", tags=["Prayer Chains"])
app.include_router(timestamp_analytics.router, prefix="/analytics/timestamps", tags=["Timestamp Analytics"])
app.include_router(analytics.router, prefix="/analytics", tags=["Church Analytics"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(websocket.router, prefix="/chat", tags=["WebSocket"])
app.include_router(recommendation.router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(bcc.router, prefix="/bcc", tags=["BCC"])
app.include_router(system_logs.router, prefix="/api/system-logs", tags=["System Logs"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(public_checkin.router, prefix="/public", tags=["Public Check-in"])
app.include_router(public_qr.router, prefix="/public", tags=["Public QR"])
app.include_router(family_role.router, prefix="/family-roles", tags=["Family Roles"])

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Create static folder if it doesn't exist
os.makedirs("static", exist_ok=True)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
