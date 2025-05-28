from typing import Dict, List, Optional, Any
import httpx

from app.schemas import BookCreate, BookFormatCreate


class GutenbergService:
    """Service for working with Gutenberg API"""
    
    def __init__(self):
        self.base_url = "https://gutendex.com/books/"
    
    async def search_books(
        self, 
        search_query: Optional[str] = None, 
        languages: Optional[List[str]] = None,
        page: int = 1,
        limit: int = 32
    ) -> Dict[str, Any]:
        """Search for books in the Gutenberg API"""
        params = {}
        
        if search_query:
            params["search"] = search_query
        
        if languages:
            params["languages"] = ",".join(languages)
        
        params["page"] = page
        
        print(f"🔍 DEBUG: Making a query to {self.base_url} with parameters {params}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                result = response.json()
                
                print(f"✅ DEBUG: Received {len(result.get('results', []))} of results")
                
                return {
                    "count": result.get("count", 0),
                    "next": result.get("next"),
                    "previous": result.get("previous"),
                    "results": result.get("results", [])
                }
        except Exception as e:
            print(f"❌ DEBUG: API request error: {e}")
            raise
    
    async def get_book_by_id(self, book_id: int) -> Dict[str, Any]:
        """Getting a book by its ID in Gutenberg"""
        url = f"https://gutendex.com/books/{book_id}/"
        print(f"🔍 DEBUG: Get a book from {url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"❌ DEBUG: Error receiving a book {book_id}: {e}")
            raise
    
    def map_gutenberg_to_book(self, gutenberg_book: Dict[str, Any]) -> Dict[str, Any]:
        """Converting data from Gutenberg into a format for our models"""
        book_data = {
            "title": gutenberg_book.get("title", "Unknown title"),
            "author": ", ".join([author.get("name", "Unknown author") for author in gutenberg_book.get("authors", [])]),
            "gutenberg_id": gutenberg_book.get("id"),
            "language": next(iter(gutenberg_book.get("languages", [])), None),
            "description": None, 
            "cover_url": None,  
        }
        
        formats = gutenberg_book.get("formats", {})
        if "image/jpeg" in formats:
            book_data["cover_url"] = formats["image/jpeg"]
        
        book_formats = []
        format_mapping = {
            "application/pdf": "pdf",
            "application/epub+zip": "epub",
            "text/html": "html",
            "text/plain": "text"
        }
        
        for format_type, url in formats.items():
            if format_type in format_mapping:
                book_formats.append({
                    "format_type": format_mapping[format_type],
                    "url": url
                })
        
        return {
            "book": book_data,
            "formats": book_formats
        }


gutendex_service = GutenbergService()