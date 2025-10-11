# ContextScope Eval

Evaluate, trace, and visualize how AI agents share and use context in multi-agent recommendation systems.

## Overview

ContextScope Eval is an evaluation framework that measures how effectively autonomous agents pass and use information through multi-agent pipelines. Built for the MongoDB hackathon, it demonstrates context transmission quality using a Netflix-like movie recommendation system with the Mflix sample dataset.

**Key Innovation:** Measures information flow quality — how context survives, transforms, and degrades as it moves through agents.

## Features

- Multi-agent movie recommendation system (User Profiler → Content Analyzer → Recommender → Explainer)
- Context fidelity and drift measurement at each agent handoff
- MongoDB Atlas integration with Vector Search
- Real-time visualization dashboard
- Comparison of structured (JSON) vs freeform (Markdown) context formats

## Quick Start

1. **Prerequisites**
   - Python 3.10+
   - MongoDB Atlas account with Mflix sample data loaded
   
2. **Setup**
   ```bash
   # Clone and enter directory
   cd mongodbhackathon
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure environment
   cp env.example .env
   # Edit .env with your MongoDB connection string
   ```

3. **Test Connection**
   ```bash
   python test_connection.py
   ```

4. **Next Steps**
   See `SETUP.md` for detailed setup instructions and usage examples.

## Project Structure

```
mongodbhackathon/
├── backend/           # Python backend with FastAPI
│   ├── config.py     # Configuration management
│   ├── db/           # MongoDB connection layer
│   ├── models/       # Data models for User, Movie, Comment
│   └── services/     # Business logic layer
├── test_connection.py # Connection test script
└── docs/
    ├── PROJECT.md    # Full project specification
    ├── SETUP.md      # Setup guide
    └── AGENTS.md     # Agent architecture details
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Database | MongoDB Atlas + Vector Search |
| Backend | Python + FastAPI |
| Models | Pydantic |
| Agents | Granite 4.0 (Apache 2.0) |
| Judge | OLMo / Mistral (Apache 2.0) |
| Frontend | Next.js + D3.js (coming soon) |

## Documentation

- `PROJECT.md` - Complete project specification and architecture
- `SETUP.md` - Setup guide and troubleshooting
- `AGENTS.md` - Agent design and implementation details

## License

Apache-2.0 (Models) / MIT (Code)
