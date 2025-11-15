from fastapi import FastAPI
from .database import init_db
from .routers import auth, sync
from .config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

app.include_router(sync.router, prefix=settings.API_V1_STR, tags=["Sync"])

@app.get("/")
def root():
    return {"message": "Password Manager Server is running"}