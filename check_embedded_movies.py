"""Check the embedded_movies collection for embedding data."""

from backend.db import get_mongo_client

client = get_mongo_client()
db = client.database

# Check embedded_movies collection
total = db.embedded_movies.count_documents({})
print(f'Total documents in embedded_movies: {total:,}')

# Check what fields exist
sample = db.embedded_movies.find_one()
if sample:
    print(f'\nSample document fields:')
    for key in sample.keys():
        value = sample[key]
        value_type = type(value).__name__
        if key == 'plot_embedding' and hasattr(value, '__len__'):
            print(f'  {key}: {value_type} (length: {len(value) if isinstance(value, (list, tuple)) else "binary"})')
        else:
            print(f'  {key}: {value_type}')
    
    print(f'\nSample movie:')
    print(f'  Title: {sample.get("title")}')
    print(f'  Year: {sample.get("year")}')
    print(f'  Genres: {sample.get("genres", [])}')
    
    # Check embedding
    if 'plot_embedding' in sample:
        emb = sample['plot_embedding']
        print(f'\nEmbedding info:')
        print(f'  Type: {type(emb)}')
        if isinstance(emb, (list, tuple)):
            print(f'  Dimension: {len(emb)}')
            print(f'  First 5 values: {emb[:5]}')
        else:
            print(f'  Binary data length: {len(emb) if hasattr(emb, "__len__") else "unknown"}')

# Check embeddings by genre
print(f'\n\nGenre breakdown:')
for genre in ['Action', 'Fantasy', 'Western']:
    count = db.embedded_movies.count_documents({'genres': genre})
    print(f'  {genre}: {count:,} movies')
    
    # Get sample
    sample = db.embedded_movies.find_one({'genres': genre})
    if sample:
        print(f'    Sample: {sample.get("title")} ({sample.get("year")})')

