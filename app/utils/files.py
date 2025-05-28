import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from uuid import uuid4

from fastapi import UploadFile

from app.config import UPLOAD_DIR_PATH

if os.getenv("RENDER"):
    UPLOAD_BASE_DIR = Path("/tmp/uploads")
else:
    UPLOAD_BASE_DIR = Path("uploads")

UPLOAD_BASE_DIR.mkdir(exist_ok=True)

def save_upload_file(upload_file: UploadFile, user_id: int) -> Tuple[str, Path]:
    """
    Saves the uploaded file to the user's directory.
    Returns the file path and file name.
    """
    filename = f"{uuid4()}_{upload_file.filename}"
    
    user_dir = UPLOAD_DIR_PATH / str(user_id)
    user_dir.mkdir(exist_ok=True)
    
    file_path = user_dir / filename
    
    print(f"📁 Saving file to: {file_path}")
    print(f"📁 User directory: {user_dir}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    relative_path = os.path.join(str(user_id), filename)
    print(f"📁 Relative path: {relative_path}")
    
    return relative_path, file_path

def get_file_info(file_path: Path) -> Dict[str, any]:
    """
    Gets information about the file (metadata, number of pages, etc.)
    depending on the file format.
    """
    info = {
        "file_size": file_path.stat().st_size,
        "file_extension": file_path.suffix.lower(),
        "pages": None,
        "title": None,
        "author": None
    }
    
    if info["file_extension"] == ".pdf":
        try:
            try:
                import PyPDF2
                
                with open(file_path, "rb") as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    info["pages"] = len(pdf_reader.pages)
                    
                    if pdf_reader.metadata:
                        if pdf_reader.metadata.title:
                            info["title"] = pdf_reader.metadata.title
                        if pdf_reader.metadata.author:
                            info["author"] = pdf_reader.metadata.author
            except ImportError:
                print("The PyPDF2 library is not installed. PDF metadata will not be processed.")
        except Exception as e:
            print(f"Error reading a PDF file: {e}")
    
    elif info["file_extension"] == ".epub":
        try:
            try:
                import ebooklib
                from ebooklib import epub
                
                book = epub.read_epub(file_path)
                
                if book.get_metadata('DC', 'title'):
                    info["title"] = book.get_metadata('DC', 'title')[0][0]
                if book.get_metadata('DC', 'creator'):
                    info["author"] = book.get_metadata('DC', 'creator')[0][0]
                
                info["pages"] = len(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            except ImportError:
                print("The ebooklib library is not installed. EPUB metadata will not be processed.")
        except Exception as e:
            print(f"Error reading an EPUB file: {e}")
    
    return info


def get_file_path(relative_path: str) -> Path:
    """
    Gets the full path to the file based on the relative path.
    """
    return UPLOAD_DIR_PATH / relative_path


def remove_file(relative_path: str) -> bool:
    """
    Deletes a file by relative path.
    Returns True if the file is successfully deleted.
    """
    file_path = get_file_path(relative_path)
    
    if file_path.exists():
        file_path.unlink()
        return True
    
    return False