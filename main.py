from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.routes import user, auth, family_member, family_activity ,family_document, announcement, shared_document,family,prayer_chain
from dotenv import load_dotenv

from app.db.init_db import init_db

load_dotenv()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

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
