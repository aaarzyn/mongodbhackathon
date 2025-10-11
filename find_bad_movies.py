"""Find movies with corrupted title field."""

from backend.db import get_mongo_client

client = get_mongo_client()
db = client.database

# Find movies where title is not a string
print("Searching for movies with non-string titles...")

count = 0
for movie in db.movies.find().limit(25000):
    title = movie.get('title')
    if title is not None and not isinstance(title, str):
        count += 1
        print(f"\nMovie with bad title #{count}:")
        print(f"  ID: {movie['_id']}")
        print(f"  Title: {title} (type: {type(title).__name__})")
        print(f"  Year: {movie.get('year')}")
        print(f"  Genres: {movie.get('genres', [])}")
        
        if count >= 10:
            break

print(f"\nTotal movies with non-string titles: {count}")

