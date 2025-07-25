from fastapi import FastAPI
from app.api.routes import user, auth, family_member, family_activity ,family_document
from dotenv import load_dotenv

from app.db.init_db import init_db

load_dotenv()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(family_member.router, prefix="/family/family-members", tags=["Family Members"])
app.include_router(family_activity.router, prefix="/family/family-activities", tags=["Activities"])
app.include_router(family_document.router, prefix="/family/family-documents", tags=["Documents"])
