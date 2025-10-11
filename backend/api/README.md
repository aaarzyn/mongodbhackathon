# FastAPI Backend

REST API for the ContextScope movie recommendation system.

## Start the Server

```bash
# Method 1: Using the start script
python start_api.py

# Method 2: Using uvicorn directly
uvicorn backend.api.app:app --reload --port 8000

# Method 3: With custom host/port
uvicorn backend.api.app:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### Health & Info
- `GET /` - Root endpoint with API info
- `GET /health` - Health check

### Users
- `GET /api/users/` - List users (with pagination)
- `GET /api/users/{email}` - Get user by email

### Movies
- `GET /api/movies/` - List/search movies
  - Query params: `skip`, `limit`, `genre`, `director`, `min_rating`, `search`
- `GET /api/movies/genres` - Get list of available genres
- `GET /api/movies/top-rated` - Get top-rated movies
- `GET /api/movies/{movie_id}` - Get movie by ID

### Recommendations
- `GET /api/recommendations/{email}` - Get personalized recommendations
  - Query params: `top_n` (default: 5)
- `GET /api/recommendations/profile/{email}` - Get user profile analysis

## Example Requests

### Get Top-Rated Movies
```bash
curl http://localhost:8000/api/movies/top-rated?limit=10&min_rating=8.0
```

### Get Movies by Genre
```bash
curl "http://localhost:8000/api/movies/?genre=Sci-Fi&limit=20"
```

### Get Personalized Recommendations
```bash
curl http://localhost:8000/api/recommendations/sean_bean@gameofthron.es?top_n=5
```

### Get User Profile
```bash
curl http://localhost:8000/api/recommendations/profile/sean_bean@gameofthron.es
```

## Response Format

### Recommendations Response
```json
{
  "user": {
    "name": "Ned Stark",
    "email": "sean_bean@gameofthron.es"
  },
  "recommendations": [
    {
      "rank": 1,
      "title": "Band of Brothers",
      "year": 2001,
      "genres": ["Action", "Drama", "History"],
      "directors": ["..."],
      "imdb_rating": 9.6,
      "confidence": 0.85,
      "explanation": "We recommend 'Band of Brothers' (2001) because...",
      "key_appeal_points": ["Genres: Action, Drama", "IMDb Rating: 9.6/10"]
    }
  ],
  "pipeline_metrics": {
    "total_execution_time_ms": 2300,
    "agents": {
      "user_profiler": {"execution_time_ms": 2100, "tokens": 101},
      "content_analyzer": {"execution_time_ms": 150, "tokens": 3176},
      "recommender": {"execution_time_ms": 1, "tokens": 639},
      "explainer": {"execution_time_ms": 1, "tokens": 662}
    }
  }
}
```

## CORS

The API is configured to allow requests from:
- `http://localhost:3000` (Next.js default dev port)
- `http://localhost:3001` (Alternative Next.js port)

## Environment Variables

Make sure `.env` file is configured:
```env
MONGO_URI=mongodb+srv://...
MONGO_DATABASE=sample_mflix
```

## Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test root endpoint
curl http://localhost:8000/

# Test recommendations (replace with actual user email)
curl http://localhost:8000/api/recommendations/sean_bean@gameofthron.es
```

