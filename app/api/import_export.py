from typing import Any, Dict, List
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.api.deps import get_current_active_user, get_db
from app.models import User, Book, BookFormat, UserBook, ReadingSession, UserActivity
from app.services.activity import activity_service

router = APIRouter(prefix="/import-export", tags=["import-export"])


@router.post("/import-library", response_model=Dict[str, Any])
async def import_library(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Importing a library from a JSON file.
    Completely replaces the user's current library.
    """
    print(f"🔄 Import request received from user {current_user.id}, filename: {file.filename}")
    
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file must be in JSON format"
        )
    
    try:
        content = await file.read()
        import_data = json.loads(content.decode('utf-8'))
        
        print(f"📖 JSON parsed successfully, data keys: {list(import_data.keys())}")
        
        if not isinstance(import_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format: JSON object expected"
            )
        
        if 'books' not in import_data or not isinstance(import_data['books'], list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format: array 'books'is missing"
            )
        
        books_to_import = import_data['books']
        print(f"📚 Found {len(books_to_import)} books to import")
        
        import_stats = {
            'total_books': len(books_to_import),
            'imported_books': 0,
            'created_books': 0,
            'skipped_books': 0,
            'errors': []
        }
        
        try:
            print(f"🗑️ Delete the current user library {current_user.id}")
            
            user_books_ids = db.query(UserBook.id).filter(UserBook.user_id == current_user.id).all()
            user_books_ids = [ub.id for ub in user_books_ids]
            
            if user_books_ids:
                deleted_sessions = db.query(ReadingSession).filter(
                    ReadingSession.user_book_id.in_(user_books_ids)
                ).delete(synchronize_session=False)
                print(f"🗑️ Deleted {deleted_sessions} read session")
            
            deleted_user_books = db.query(UserBook).filter(UserBook.user_id == current_user.id).delete()
            print(f"🗑️ Deleted {deleted_user_books} UserBook records")
            
            deleted_activities = db.query(UserActivity).filter(
                and_(
                    UserActivity.user_id == current_user.id,
                    UserActivity.book_id.isnot(None)
                )
            ).delete()
            print(f"🗑️ Deleted {deleted_activities} activities")
            
            db.commit()
            print("💾 Interim committee completed")
            
            print(f"🔍 Search for orphan books...")
            try:
                orphaned_book_ids = db.execute("""
                    SELECT b.id FROM books b 
                    LEFT JOIN user_books ub ON b.id = ub.book_id 
                    WHERE ub.book_id IS NULL
                """).fetchall()
                
                orphaned_count = len(orphaned_book_ids)
                print(f"🗑️ Found {orphaned_count} orphan books")
                
                if orphaned_count > 0:
                    orphaned_ids = [row[0] for row in orphaned_book_ids]
                    
                    db.execute(f"""
                        DELETE FROM book_formats 
                        WHERE book_id IN ({','.join(map(str, orphaned_ids))})
                    """)
                    
                    db.execute(f"""
                        DELETE FROM books 
                        WHERE id IN ({','.join(map(str, orphaned_ids))})
                    """)
                    
                print(f"🗑️ Deleted {orphaned_count} orphan books")
            except Exception as cleanup_error:
                print(f"⚠️ Error clearing orphan books: {cleanup_error}")
            
            print(f"📚 Starting imports of {len(books_to_import)} books")
            
            for i, book_data in enumerate(books_to_import):
                try:
                    if i % 5 == 0:
                        print(f"📖 Processing book {i+1}/{len(books_to_import)}")
                    
                    if not isinstance(book_data, dict) or 'book' not in book_data:
                        error_msg = f"Incorrect book structure #{i+1}"
                        import_stats['errors'].append(error_msg)
                        import_stats['skipped_books'] += 1
                        continue
                    
                    book_info = book_data['book']
                    user_book_info = {
                        'status': book_data.get('status', 'Want to read'),
                        'bookmark_position': book_data.get('bookmark_position', 0),
                        'is_local': book_data.get('is_local', False),
                        'file_path': book_data.get('file_path'),
                        'added_at': book_data.get('added_at')
                    }
                    
                    existing_book = None
                    
                    if book_info.get('gutenberg_id'):
                        existing_book = db.query(Book).filter(
                            Book.gutenberg_id == book_info['gutenberg_id']
                        ).first()
                    
                    if not existing_book and book_info.get('title') and book_info.get('author'):
                        existing_book = db.query(Book).filter(
                            and_(
                                Book.title == book_info['title'],
                                Book.author == book_info['author']
                            )
                        ).first()
                    
                    if existing_book:
                        db_book = existing_book
                        if i < 3:  
                            print(f"📖 Use an existing book: {db_book.title}")
                    else:
                        book_create_data = {
                            'title': book_info.get('title', 'Невідома книга'),
                            'author': book_info.get('author'),
                            'description': book_info.get('description'),
                            'language': book_info.get('language'),
                            'gutenberg_id': book_info.get('gutenberg_id'),
                            'cover_url': book_info.get('cover_url')
                        }
                        
                        db_book = Book(**book_create_data)
                        db.add(db_book)
                        db.flush() 
                        
                        if 'formats' in book_info and isinstance(book_info['formats'], list):
                            for format_data in book_info['formats']:
                                if isinstance(format_data, dict) and 'format_type' in format_data and 'url' in format_data:
                                    db_format = BookFormat(
                                        book_id=db_book.id,
                                        format_type=format_data['format_type'],
                                        url=format_data['url']
                                    )
                                    db.add(db_format)
                        
                        import_stats['created_books'] += 1
                        if i < 3:  
                            print(f"📚+ A new book has been created: {db_book.title}")
                    
                    added_at = None
                    if user_book_info['added_at']:
                        try:
                            added_at = datetime.fromisoformat(user_book_info['added_at'].replace('Z', '+00:00'))
                        except:
                            added_at = datetime.now()
                    else:
                        added_at = datetime.now()
                    
                    db_user_book = UserBook(
                        user_id=current_user.id,
                        book_id=db_book.id,
                        status=user_book_info['status'],
                        bookmark_position=user_book_info['bookmark_position'] or 0,
                        is_local=user_book_info['is_local'],
                        file_path=user_book_info['file_path'],
                        added_at=added_at
                    )
                    db.add(db_user_book)
                    
                    import_stats['imported_books'] += 1
                    
                    if (i + 1) % 10 == 0:
                        db.commit()
                        print(f"💾 Interim committee after {i + 1} books")
                    
                except Exception as e:
                    error_msg = f"Error importing a book #{i+1} '{book_data.get('book', {}).get('title', 'Unknown')}': {str(e)}"
                    import_stats['errors'].append(error_msg)
                    import_stats['skipped_books'] += 1
                    print(f"❌ {error_msg}")
                    continue
            
            print("💾 Committing changes to database...")
            db.commit()
            
            try:
                activity_service.log_activity(
                    db=db,
                    user_id=current_user.id,
                    activity_type="data_imported",
                    details={
                        'total_books': import_stats['total_books'],
                        'imported_books': import_stats['imported_books'],
                        'created_books': import_stats['created_books'],
                        'skipped_books': import_stats['skipped_books'],
                        'import_date': datetime.now().isoformat(),
                        'filename': file.filename
                    }
                )
            except Exception as e:
                print(f"⚠️ Error logging import activity: {e}")
            
            print(f"✅ Import completed successfully")
            
            return {
                "message": "Library import completed successfully!",
                "statistics": import_stats,
                "success": True
            }
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error during import: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during import: {str(e)}"
            )
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect JSON format: {str(e)}"
        )
    except Exception as e:
        print(f"❌ General error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File processing error: {str(e)}"
        )