from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
    debug=DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
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


from fastapi.responses import FileResponse

@app.get("/")
async def read_index():
    """
    Serve the main page
    """
    return FileResponse('app/static/index.html')


@app.get("/api")
async def api_info():
    """
    API information endpoint
    """
    return {
        "message": "Welcome to the OwnLib API",
        "docs": "/docs",
        "redoc": "/redoc", 
        "version": "1.0.0"
    }


@app.get("/catalog")
async def catalog():
    return FileResponse('app/static/catalog.html')


@app.get("/profile") 
async def profile():
    return FileResponse('app/static/profile.html')


@app.get("/faq")
async def faq():
    return FileResponse('app/static/faq.html')


@app.get("/health")
async def health_check():
    """
    Check the status of the application
    """
    return {
        "status": "healthy",
        "version": "1.0.0"
    }