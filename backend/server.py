from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import requests
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# TMDB Configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

# Create the main app
app = FastAPI(title="Movie Discovery API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# TMDB Service Class
class TMDBService:
    def __init__(self):
        self.api_key = TMDB_API_KEY
        self.base_url = TMDB_BASE_URL
        self.image_base_url = TMDB_IMAGE_BASE_URL
        
        if not self.api_key:
            raise ValueError("TMDB_API_KEY environment variable is required")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to TMDB API"""
        if params is None:
            params = {}
        
        params['api_key'] = self.api_key
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"TMDB API error: {str(e)}")
    
    def get_popular_movies(self, page: int = 1) -> Dict:
        """Get popular movies"""
        return self._make_request("/movie/popular", {"page": page})
    
    def get_popular_tv_shows(self, page: int = 1) -> Dict:
        """Get popular TV shows"""
        return self._make_request("/tv/popular", {"page": page})
    
    def discover_movies(self, genre_ids: List[int] = None, page: int = 1, 
                       sort_by: str = "popularity.desc") -> Dict:
        """Discover movies with filters"""
        params = {
            "page": page,
            "sort_by": sort_by
        }
        
        if genre_ids:
            params["with_genres"] = ",".join(map(str, genre_ids))
        
        return self._make_request("/discover/movie", params)
    
    def discover_tv_shows(self, genre_ids: List[int] = None, page: int = 1,
                         sort_by: str = "popularity.desc") -> Dict:
        """Discover TV shows with filters"""
        params = {
            "page": page,
            "sort_by": sort_by
        }
        
        if genre_ids:
            params["with_genres"] = ",".join(map(str, genre_ids))
        
        return self._make_request("/discover/tv", params)
    
    def get_movie_genres(self) -> Dict:
        """Get list of movie genres"""
        return self._make_request("/genre/movie/list")
    
    def get_tv_genres(self) -> Dict:
        """Get list of TV show genres"""
        return self._make_request("/genre/tv/list")
    
    def get_image_url(self, file_path: str, size: str = "w500") -> str:
        """Generate full image URL"""
        if not file_path:
            return ""
        return f"{self.image_base_url}{size}{file_path}"

# Initialize TMDB service
tmdb_service = TMDBService()

# Pydantic Models
class SwipeAction(BaseModel):
    content_id: int
    content_type: str  # "movie" or "tv"
    action: str  # "like" or "dislike"
    user_id: Optional[str] = "default_user"

class DiscoverRequest(BaseModel):
    content_type: str  # "movie" or "tv"
    genre_ids: Optional[List[int]] = None
    page: int = 1
    sort_by: str = "popularity.desc"

class UserProgress(BaseModel):
    content_id: int
    content_type: str
    status: str  # "watching", "completed", "want_to_watch"
    progress: int = 0  # For TV shows, episode number
    user_id: Optional[str] = "default_user"

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Movie Discovery API is running"}

@api_router.get("/genres/movies")
async def get_movie_genres():
    """Get all movie genres"""
    try:
        genres = tmdb_service.get_movie_genres()
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/genres/tv")
async def get_tv_genres():
    """Get all TV show genres"""
    try:
        genres = tmdb_service.get_tv_genres()
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/discover")
async def discover_content(request: DiscoverRequest):
    """Discover movies or TV shows based on filters"""
    try:
        if request.content_type == "movie":
            data = tmdb_service.discover_movies(
                genre_ids=request.genre_ids,
                page=request.page,
                sort_by=request.sort_by
            )
        elif request.content_type == "tv":
            data = tmdb_service.discover_tv_shows(
                genre_ids=request.genre_ids,
                page=request.page,
                sort_by=request.sort_by
            )
        else:
            raise HTTPException(status_code=400, detail="content_type must be 'movie' or 'tv'")
        
        # Add full image URLs
        for item in data.get("results", []):
            if item.get("poster_path"):
                item["poster_url"] = tmdb_service.get_image_url(item["poster_path"])
            if item.get("backdrop_path"):
                item["backdrop_url"] = tmdb_service.get_image_url(item["backdrop_path"], "w1280")
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/swipe")
async def record_swipe_action(action: SwipeAction):
    """Record user swipe action (like/dislike)"""
    try:
        swipe_collection = db["user_swipes"]
        
        # Check if user already swiped on this content
        existing_swipe = await swipe_collection.find_one({
            "content_id": action.content_id,
            "content_type": action.content_type,
            "user_id": action.user_id
        })
        
        if existing_swipe:
            # Update existing swipe
            await swipe_collection.update_one(
                {"_id": existing_swipe["_id"]},
                {"$set": {"action": action.action, "updated_at": datetime.utcnow()}}
            )
        else:
            # Create new swipe record
            swipe_data = {
                "id": str(uuid.uuid4()),
                "content_id": action.content_id,
                "content_type": action.content_type,
                "action": action.action,
                "user_id": action.user_id,
                "created_at": datetime.utcnow()
            }
            await swipe_collection.insert_one(swipe_data)
        
        return {"message": "Swipe recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/liked/{user_id}")
async def get_user_liked_content(user_id: str = "default_user"):
    """Get user's liked content"""
    try:
        swipe_collection = db["user_swipes"]
        
        # Get user's liked content
        liked_content = await swipe_collection.find({
            "user_id": user_id,
            "action": "like"
        }).to_list(length=None)
        
        return {"liked_content": liked_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/progress")
async def update_progress(progress: UserProgress):
    """Update user's watching progress"""
    try:
        progress_collection = db["user_progress"]
        
        # Check if progress entry exists
        existing_progress = await progress_collection.find_one({
            "content_id": progress.content_id,
            "content_type": progress.content_type,
            "user_id": progress.user_id
        })
        
        if existing_progress:
            # Update existing progress
            await progress_collection.update_one(
                {"_id": existing_progress["_id"]},
                {"$set": {
                    "status": progress.status,
                    "progress": progress.progress,
                    "updated_at": datetime.utcnow()
                }}
            )
        else:
            # Create new progress record
            progress_data = {
                "id": str(uuid.uuid4()),
                "content_id": progress.content_id,
                "content_type": progress.content_type,
                "status": progress.status,
                "progress": progress.progress,
                "user_id": progress.user_id,
                "created_at": datetime.utcnow()
            }
            await progress_collection.insert_one(progress_data)
        
        return {"message": "Progress updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/progress/{user_id}")
async def get_user_progress(user_id: str = "default_user"):
    """Get user's watching progress"""
    try:
        progress_collection = db["user_progress"]
        
        # Get user's progress
        progress_data = await progress_collection.find({
            "user_id": user_id
        }).to_list(length=None)
        
        return {"progress": progress_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/stats/{user_id}")
async def get_user_stats(user_id: str = "default_user"):
    """Get user statistics"""
    try:
        swipe_collection = db["user_swipes"]
        progress_collection = db["user_progress"]
        
        # Get swipe stats
        total_swipes = await swipe_collection.count_documents({"user_id": user_id})
        liked_count = await swipe_collection.count_documents({"user_id": user_id, "action": "like"})
        disliked_count = await swipe_collection.count_documents({"user_id": user_id, "action": "dislike"})
        
        # Get progress stats
        watching_count = await progress_collection.count_documents({"user_id": user_id, "status": "watching"})
        completed_count = await progress_collection.count_documents({"user_id": user_id, "status": "completed"})
        
        return {
            "stats": {
                "total_swipes": total_swipes,
                "liked_count": liked_count,
                "disliked_count": disliked_count,
                "watching_count": watching_count,
                "completed_count": completed_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()