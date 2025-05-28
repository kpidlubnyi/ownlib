import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DB_DRIVER = os.getenv("DB_DRIVER", "mysql+pymysql")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("Не налаштовані всі необхідні змінні бази даних")

DATABASE_URL = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY має бути встановлений")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

GUTENBERG_API_URL = os.getenv("GUTENBERG_API_URL", "https://gutendex.com/books/")

UPLOAD_DIRECTORY = Path(os.getenv("UPLOAD_DIRECTORY", "uploads"))
UPLOAD_DIR_PATH = BASE_DIR / UPLOAD_DIRECTORY
UPLOAD_DIR_PATH.mkdir(exist_ok=True)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "pdf,epub,html,txt").split(",")

DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))