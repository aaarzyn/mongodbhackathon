"""Debug script to find the problematic movie for sean_bean."""

from backend.db import get_mongo_client
from backend.services import MflixService
from backend.models.movie import Movie
from backend.utils.mongo_helpers import convert_objectid_to_str

client = get_mongo_client()
service = MflixService(client)

# Get sean_bean's comments
email = 'sean_bean@gameofthron.es'
comments = service.get_comments_by_user(email, limit=100)

print(f"Checking {len(comments)} comments for {email}")

# Try to get each movie
for i, comment in enumerate(comments, 1):
    try:
        movie = service.get_movie_by_id(comment.movie_id)
        if movie:
            print(f"{i}. ✓ {movie.title} ({movie.year})")
        else:
            print(f"{i}. ⚠ Movie not found: {comment.movie_id}")
    except Exception as e:
        print(f"{i}. ✗ ERROR getting movie {comment.movie_id}: {e}")
        
        # Try to get the raw document
        raw_movie = client.database.movies.find_one({'_id': comment.movie_id})
        if raw_movie:
            print(f"   Raw title: {raw_movie.get('title')} (type: {type(raw_movie.get('title')).__name__})")
            
            # Test converter
            converted = convert_objectid_to_str(raw_movie)
            print(f"   Converted title: {converted.get('title')} (type: {type(converted.get('title')).__name__})")
            
            # Try to create Movie object
            try:
                movie_obj = Movie(**converted)
                print(f"   ✓ Movie object created: {movie_obj.title}")
            except Exception as e2:
                print(f"   ✗ Movie validation failed: {e2}")

