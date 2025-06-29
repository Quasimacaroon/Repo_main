#!/usr/bin/env python3
import requests
import json
import unittest
import os
import sys
from dotenv import load_dotenv

# Load environment variables from frontend/.env to get the backend URL
load_dotenv('/app/frontend/.env')

# Get the backend URL from environment variables
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in environment variables")
    sys.exit(1)

# Ensure the URL ends with /api
API_URL = f"{BACKEND_URL}/api"
print(f"Testing API at: {API_URL}")

class MovieDiscoveryAPITest(unittest.TestCase):
    """Test suite for the Movie Discovery API"""

    def test_01_health_check(self):
        """Test the API health check endpoint"""
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Movie Discovery API is running")
        print("✅ Health check endpoint is working")

    def test_02_get_movie_genres(self):
        """Test the movie genres endpoint"""
        response = requests.get(f"{API_URL}/genres/movies")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("genres", data)
        self.assertTrue(len(data["genres"]) > 0)
        # Check if genres have id and name fields
        for genre in data["genres"]:
            self.assertIn("id", genre)
            self.assertIn("name", genre)
        print(f"✅ Movie genres endpoint returned {len(data['genres'])} genres")

    def test_03_get_tv_genres(self):
        """Test the TV genres endpoint"""
        response = requests.get(f"{API_URL}/genres/tv")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("genres", data)
        self.assertTrue(len(data["genres"]) > 0)
        # Check if genres have id and name fields
        for genre in data["genres"]:
            self.assertIn("id", genre)
            self.assertIn("name", genre)
        print(f"✅ TV genres endpoint returned {len(data['genres'])} genres")

    def test_04_discover_movies(self):
        """Test the discover movies endpoint"""
        payload = {
            "content_type": "movie",
            "page": 1,
            "sort_by": "popularity.desc"
        }
        response = requests.post(f"{API_URL}/discover", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertTrue(len(data["results"]) > 0)
        
        # Check if movies have required fields and image URLs
        for movie in data["results"]:
            self.assertIn("id", movie)
            self.assertIn("title", movie)
            if "poster_path" in movie and movie["poster_path"]:
                self.assertIn("poster_url", movie)
                self.assertTrue(movie["poster_url"].startswith("https://image.tmdb.org/t/p/"))
            if "backdrop_path" in movie and movie["backdrop_path"]:
                self.assertIn("backdrop_url", movie)
                self.assertTrue(movie["backdrop_url"].startswith("https://image.tmdb.org/t/p/"))
        
        print(f"✅ Discover movies endpoint returned {len(data['results'])} movies")

    def test_05_discover_tv(self):
        """Test the discover TV shows endpoint"""
        payload = {
            "content_type": "tv",
            "page": 1,
            "sort_by": "popularity.desc"
        }
        response = requests.post(f"{API_URL}/discover", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertTrue(len(data["results"]) > 0)
        
        # Check if TV shows have required fields and image URLs
        for show in data["results"]:
            self.assertIn("id", show)
            self.assertIn("name", show)
            if "poster_path" in show and show["poster_path"]:
                self.assertIn("poster_url", show)
                self.assertTrue(show["poster_url"].startswith("https://image.tmdb.org/t/p/"))
            if "backdrop_path" in show and show["backdrop_path"]:
                self.assertIn("backdrop_url", show)
                self.assertTrue(show["backdrop_url"].startswith("https://image.tmdb.org/t/p/"))
        
        print(f"✅ Discover TV shows endpoint returned {len(data['results'])} shows")

    def test_06_discover_with_genre_filter(self):
        """Test the discover endpoint with genre filtering"""
        # First get movie genres
        genres_response = requests.get(f"{API_URL}/genres/movies")
        genres_data = genres_response.json()
        
        # Use the first genre for filtering
        if len(genres_data["genres"]) > 0:
            genre_id = genres_data["genres"][0]["id"]
            
            payload = {
                "content_type": "movie",
                "genre_ids": [genre_id],
                "page": 1
            }
            response = requests.post(f"{API_URL}/discover", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("results", data)
            
            print(f"✅ Discover with genre filter returned {len(data['results'])} results")
        else:
            self.fail("No genres available for testing")

    def test_07_swipe_action(self):
        """Test the swipe action endpoint"""
        # First discover a movie to get a valid content_id
        discover_payload = {
            "content_type": "movie",
            "page": 1
        }
        discover_response = requests.post(f"{API_URL}/discover", json=discover_payload)
        discover_data = discover_response.json()
        
        if len(discover_data["results"]) > 0:
            movie = discover_data["results"][0]
            content_id = movie["id"]
            
            # Test like action
            like_payload = {
                "content_id": content_id,
                "content_type": "movie",
                "action": "like",
                "user_id": "test_user"
            }
            like_response = requests.post(f"{API_URL}/swipe", json=like_payload)
            self.assertEqual(like_response.status_code, 200)
            like_data = like_response.json()
            self.assertEqual(like_data["message"], "Swipe recorded successfully")
            
            # Test dislike action
            dislike_payload = {
                "content_id": content_id,
                "content_type": "movie",
                "action": "dislike",
                "user_id": "test_user"
            }
            dislike_response = requests.post(f"{API_URL}/swipe", json=dislike_payload)
            self.assertEqual(dislike_response.status_code, 200)
            dislike_data = dislike_response.json()
            self.assertEqual(dislike_data["message"], "Swipe recorded successfully")
            
            print("✅ Swipe action endpoint is working for both like and dislike")
        else:
            self.fail("No movies available for testing swipe action")

    def test_08_get_liked_content(self):
        """Test the get liked content endpoint"""
        # First add a like for a movie
        discover_payload = {
            "content_type": "movie",
            "page": 1
        }
        discover_response = requests.post(f"{API_URL}/discover", json=discover_payload)
        discover_data = discover_response.json()
        
        if len(discover_data["results"]) > 0:
            movie = discover_data["results"][0]
            content_id = movie["id"]
            
            # Add a like
            like_payload = {
                "content_id": content_id,
                "content_type": "movie",
                "action": "like",
                "user_id": "test_user_likes"
            }
            requests.post(f"{API_URL}/swipe", json=like_payload)
            
            # Get liked content
            response = requests.get(f"{API_URL}/liked/test_user_likes")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("liked_content", data)
            
            # Check if the liked content contains our movie
            found = False
            for item in data["liked_content"]:
                if item["content_id"] == content_id and item["content_type"] == "movie":
                    found = True
                    break
            
            self.assertTrue(found, "Liked movie not found in liked content")
            print(f"✅ Get liked content endpoint returned {len(data['liked_content'])} items")
        else:
            self.fail("No movies available for testing liked content")

    def test_09_progress_tracking(self):
        """Test the progress tracking endpoints"""
        # First discover a TV show to get a valid content_id
        discover_payload = {
            "content_type": "tv",
            "page": 1
        }
        discover_response = requests.post(f"{API_URL}/discover", json=discover_payload)
        discover_data = discover_response.json()
        
        if len(discover_data["results"]) > 0:
            show = discover_data["results"][0]
            content_id = show["id"]
            
            # Update progress
            progress_payload = {
                "content_id": content_id,
                "content_type": "tv",
                "status": "watching",
                "progress": 3,  # Episode 3
                "user_id": "test_user_progress"
            }
            progress_response = requests.post(f"{API_URL}/progress", json=progress_payload)
            self.assertEqual(progress_response.status_code, 200)
            progress_data = progress_response.json()
            self.assertEqual(progress_data["message"], "Progress updated successfully")
            
            # Get progress
            get_progress_response = requests.get(f"{API_URL}/progress/test_user_progress")
            self.assertEqual(get_progress_response.status_code, 200)
            get_progress_data = get_progress_response.json()
            self.assertIn("progress", get_progress_data)
            
            # Check if the progress contains our TV show
            found = False
            for item in get_progress_data["progress"]:
                if item["content_id"] == content_id and item["content_type"] == "tv":
                    found = True
                    self.assertEqual(item["status"], "watching")
                    self.assertEqual(item["progress"], 3)
                    break
            
            self.assertTrue(found, "TV show progress not found")
            print(f"✅ Progress tracking endpoints are working")
        else:
            self.fail("No TV shows available for testing progress")

    def test_10_user_stats(self):
        """Test the user stats endpoint"""
        # First add some swipes and progress for a specific test user
        discover_payload = {
            "content_type": "movie",
            "page": 1
        }
        discover_response = requests.post(f"{API_URL}/discover", json=discover_payload)
        discover_data = discover_response.json()
        
        if len(discover_data["results"]) > 0:
            # Add likes and dislikes
            for i, movie in enumerate(discover_data["results"][:3]):
                content_id = movie["id"]
                action = "like" if i % 2 == 0 else "dislike"
                
                swipe_payload = {
                    "content_id": content_id,
                    "content_type": "movie",
                    "action": action,
                    "user_id": "test_user_stats"
                }
                requests.post(f"{API_URL}/swipe", json=swipe_payload)
            
            # Add progress
            if len(discover_data["results"]) >= 2:
                progress_payload = {
                    "content_id": discover_data["results"][1]["id"],
                    "content_type": "movie",
                    "status": "completed",
                    "progress": 100,
                    "user_id": "test_user_stats"
                }
                requests.post(f"{API_URL}/progress", json=progress_payload)
            
            # Get stats
            stats_response = requests.get(f"{API_URL}/stats/test_user_stats")
            self.assertEqual(stats_response.status_code, 200)
            stats_data = stats_response.json()
            self.assertIn("stats", stats_data)
            
            # Check stats fields
            stats = stats_data["stats"]
            self.assertIn("total_swipes", stats)
            self.assertIn("liked_count", stats)
            self.assertIn("disliked_count", stats)
            self.assertIn("watching_count", stats)
            self.assertIn("completed_count", stats)
            
            # Verify stats are accurate
            self.assertTrue(stats["total_swipes"] >= 3)
            self.assertTrue(stats["liked_count"] >= 2)
            self.assertTrue(stats["disliked_count"] >= 1)
            self.assertTrue(stats["completed_count"] >= 1)
            
            print(f"✅ User stats endpoint is working")
            print(f"   Stats: {json.dumps(stats, indent=2)}")
        else:
            self.fail("No movies available for testing stats")


if __name__ == "__main__":
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)