# Setup Guide - ContextScope Eval

This guide will help you set up the MongoDB Atlas connection and run your first queries on the Mflix dataset.

## Prerequisites

- Python 3.10 or higher
- MongoDB Atlas account with a cluster
- Mflix sample dataset loaded in your cluster

## Step 1: Load Sample Data into MongoDB Atlas

If you haven't already loaded the Mflix sample data:

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com)
2. Select your cluster
3. Click on the "..." (More Options) button
4. Select "Load Sample Dataset"
5. Wait for the data to load (this may take a few minutes)

## Step 2: Get Your MongoDB Connection String

1. In MongoDB Atlas, click "Connect" on your cluster
2. Choose "Connect your application"
3. Copy the connection string (looks like `mongodb+srv://...`)
4. Replace `<password>` with your actual password

## Step 3: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp env.example .env

# Edit .env with your favorite editor
nano .env
```

Update the `.env` file with your MongoDB connection string:

```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGO_DATABASE=sample_mflix
DEBUG=True
LOG_LEVEL=INFO
```

**Important:** Replace `<username>`, `<password>`, and `<cluster>` with your actual credentials.

## Step 5: Test Your Connection

Run the test script to verify everything is working:

```bash
python test_connection.py
```

You should see output like:

```
============================================================
MongoDB Atlas Connection Test
============================================================
2024-10-11 10:00:00 - INFO - Testing MongoDB Atlas connection...
2024-10-11 10:00:00 - INFO - Connecting to database: sample_mflix
2024-10-11 10:00:01 - INFO - ✓ Successfully connected to MongoDB Atlas!

Listing collections in the database...
✓ Found 5 collections:
  - comments
  - movies
  - sessions
  - theaters
  - users

Getting database statistics...
✓ Database: sample_mflix
  Collections:
    - users: 185 documents
    - movies: 23,539 documents
    - comments: 50,304 documents
  Average movie rating: 6.94

Querying sample users...
✓ Retrieved 3 users:
  - Ned Stark (sean_bean@gameofthron.es)
  - ...

============================================================
Test Summary
============================================================
Passed: 6/6
Failed: 0/6

✓ All tests passed! Your MongoDB Atlas connection is working.
```

## Step 6: Explore the Code

### Project Structure

```
mongodbhackathon/
├── backend/
│   ├── config.py              # Configuration management
│   ├── db/
│   │   ├── mongo_client.py    # MongoDB connection client
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py           # User data models
│   │   ├── movie.py          # Movie data models
│   │   └── __init__.py
│   ├── services/
│   │   ├── mflix_service.py  # Service layer for Mflix operations
│   │   └── __init__.py
│   └── __init__.py
├── test_connection.py         # Connection test script
├── requirements.txt           # Python dependencies
├── env.example               # Example environment variables
└── .env                      # Your environment variables (not in git)
```

### Key Components

1. **`backend/config.py`**: Manages configuration using Pydantic settings
2. **`backend/db/mongo_client.py`**: MongoDB connection with proper error handling
3. **`backend/models/`**: Pydantic models for User, Movie, and Comment
4. **`backend/services/mflix_service.py`**: High-level API for querying the database

## Usage Examples

### Python Interactive Shell

```python
# Start Python shell
python

# Import and initialize
from backend.config import get_settings
from backend.db import get_mongo_client
from backend.services import MflixService

# Connect to database
client = get_mongo_client()
service = MflixService(client)

# Get top-rated movies
movies = service.get_top_rated_movies(limit=5, min_rating=8.5)
for movie in movies:
    print(f"{movie.title} ({movie.year}) - {movie.imdb.rating}")

# Search for Sci-Fi movies
scifi = service.get_movies_by_genre("Sci-Fi", limit=10)
for movie in scifi:
    print(f"{movie.title} - {movie.directors}")

# Get Christopher Nolan movies
nolan = service.get_movies_by_director("Christopher Nolan")
for movie in nolan:
    print(f"{movie.title} ({movie.year})")

# Get a user by email
user = service.get_user_by_email("sean_bean@gameofthron.es")
if user:
    print(f"Found user: {user.name}")
```

## Troubleshooting

### Connection Timeout

If you get a timeout error:
1. Check your MongoDB Atlas IP whitelist
2. Add your current IP or use `0.0.0.0/0` for testing (not recommended for production)
3. Verify your connection string is correct

### Authentication Failed

If you get an authentication error:
1. Verify your username and password in the connection string
2. Make sure special characters in the password are URL-encoded
3. Check that your database user has the correct permissions

### Module Not Found

If you get import errors:
1. Make sure you're in the virtual environment: `source venv/bin/activate`
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Make sure you're running Python from the project root

## Next Steps

Now that your connection is working, you can:

1. Build the recommendation agents (User Profiler, Content Analyzer, etc.)
2. Implement the context evaluation metrics
3. Create the FastAPI backend
4. Build the visualization dashboard

Refer to `PROJECT.md` for the full architecture and implementation plan.

## Need Help?

- MongoDB Atlas Docs: https://docs.atlas.mongodb.com/
- Mflix Sample Data: https://www.mongodb.com/docs/atlas/sample-data/sample-mflix/
- PyMongo Docs: https://pymongo.readthedocs.io/

