# ContextScope Movies - Frontend

Interactive movie catalog and recommendation portal built with Next.js 15, TypeScript, and Tailwind CSS.

## Features

- **Movie Catalog**: Browse top-rated movies, filter by genre
- **Personalized Recommendations**: Get AI-powered recommendations based on viewing history
- **Multi-Agent Pipeline**: Visualize the 4-agent recommendation process
- **Real-time Metrics**: See pipeline performance and confidence scores

## Prerequisites

1. **FastAPI Backend** must be running on port 8000:
   ```bash
   # In the project root
   python start_api.py
   ```

2. **MongoDB Atlas** connection configured in `.env`

## Getting Started

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm run dev
```

The app will be available at: http://localhost:3000

## Pages

### Homepage (`/`)
- Browse top-rated movies
- Filter by genre (Action, Sci-Fi, Drama, etc.)
- View movie details (ratings, directors, cast)

### Recommendations (`/recommendations`)
- Enter user email
- Get personalized recommendations
- See AI explanations for each recommendation
- View pipeline performance metrics

## API Connection

The frontend connects to the FastAPI backend at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL` in `.env.local`).

API Endpoints used:
- `/api/movies/` - Get movie catalog
- `/api/movies/genres` - Get available genres
- `/api/recommendations/{email}` - Get personalized recommendations

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **React Hooks** - State management

## Development

```bash
# Install dependencies
npm install

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Environment Variables

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx                 # Homepage (movie catalog)
│   ├── recommendations/
│   │   └── page.tsx            # Recommendations page
│   ├── layout.tsx              # Root layout
│   └── globals.css             # Global styles
├── lib/
│   └── api.ts                  # API client utilities
├── public/                     # Static assets
└── README.md                   # This file
```

## Usage Example

1. **Browse Movies**:
   - Visit http://localhost:3000
   - Click genre filters to browse by category
   - View top-rated movies with IMDb ratings

2. **Get Recommendations**:
   - Click "Get Recommendations" button
   - Enter user email (e.g., `sean_bean@gameofthron.es`)
   - Click "Get Recommendations"
   - View personalized movies with AI explanations

## Pipeline Visualization

The recommendations page shows:
- 4-agent pipeline execution flow
- Individual agent execution times
- Total pipeline latency
- Number of candidates analyzed
- Confidence scores for each recommendation

## Next Steps

- Add D3.js visualizations for agent flow
- Add context evaluation metrics
- Add user interaction tracking for Evaluator agent
- Add movie details modal
- Add user profile page
