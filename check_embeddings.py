"""Check embedding data in the movies collection."""

from backend.db import get_mongo_client

client = get_mongo_client()
db = client.database

# Check if movies have plot_embedding field
movies_with_embeddings = db.movies.count_documents({'plot_embedding': {'$exists': True, '$ne': None}})
total_movies = db.movies.count_documents({})

print(f'Total movies: {total_movies:,}')
print(f'Movies with embeddings: {movies_with_embeddings:,}')
print(f'Percentage: {movies_with_embeddings/total_movies*100:.1f}%')

# Check embedding in specific genres
for genre in ['Action', 'Fantasy', 'Western']:
    genre_count = db.movies.count_documents({'genres': genre})
    genre_with_emb = db.movies.count_documents({
        'genres': genre,
        'plot_embedding': {'$exists': True, '$ne': None}
    })
    print(f'\n{genre}:')
    print(f'  Total: {genre_count:,}')
    print(f'  With embeddings: {genre_with_emb:,}')
    
    # Get sample movie
    sample = db.movies.find_one({
        'genres': genre,
        'plot_embedding': {'$exists': True, '$ne': None}
    })
    if sample:
        print(f'  Sample: {sample["title"]} ({sample.get("year")})')
        embedding = sample.get('plot_embedding')
        if embedding:
            print(f'  Embedding type: {type(embedding).__name__}')
            if isinstance(embedding, (list, tuple)):
                print(f'  Embedding dimension: {len(embedding)}')
                print(f'  First 5 values: {embedding[:5]}')

