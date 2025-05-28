import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router  
from app.api.books import router as books_router
from app.api.files import router as files_router
from app.api.reading import router as reading_router
from app.api.stats import router as stats_router
from app.api.user_library import router as library_router
from app.api.import_export import router as import_export_router 
from app.config import DEBUG, UPLOAD_DIR_PATH, ALLOWED_ORIGINS

app = FastAPI(
    title="OwnLib API",
    description="API for the OwnLib digital library",
    version="1.0.0",
    debug=DEBUG,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None
)

if not DEBUG:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*.render.com", "localhost"]
    )

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR_PATH)), name="uploads")

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(books_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(reading_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(import_export_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Welcome to the OwnLib API",
        "version": "1.0.0",
        "environment": "production" if not DEBUG else "development"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": "production" if not DEBUG else "development"
    }