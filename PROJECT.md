# ContextScope Eval
Evaluate, trace, and visualize how AI agents share and use context.
Compliant with open-source licensing rules, designed for extensibility to enterprise-grade evaluation after the event.

## Overview

ContextScope Eval is an open-source evaluation and observability framework for agent-to-agent context sharing.
It measures how effectively autonomous agents pass and use information — tracking context fidelity, relevance drift, temporal coherence, and utility across multi-agent pipelines.

Unlike traditional LLM benchmarks (which focus on accuracy or helpfulness), ContextScope measures information flow quality — how context survives, transforms, and degrades as it moves through agents.

## Problem Statement

As multi-agent systems grow more complex, evaluating how well agents communicate and share memory becomes essential.
Current evaluation tools (LangSmith, Braintrust, Traceloop) focus on reasoning steps or final outputs — not on context transmission itself.

ContextScope Eval fills this gap.

## Key Idea

What if we could see and measure how well one agent’s context is understood by another?

ContextScope does exactly that. It introduces a new set of evaluation primitives to quantify:

| Metric | Description |
|---------|--------------|
| Context Transmission Fidelity | Percentage of relevant information successfully transmitted |
| Relevance Drift | Semantic deviation of downstream agent’s focus |
| Compression Efficiency | Token reduction versus information loss |
| Temporal Coherence | Accuracy of time-dependent or sequential context |
| Response Utility | Task performance improvement due to shared context |

## Architecture

```
contextscope-eval/
├── backend/
│   ├── app.py                # FastAPI entrypoint for eval runs and dashboard API
│   ├── evaluator/
│   │   ├── metrics.py        # Context scoring functions
│   │   └── schema.py         # MongoDB document schema
│   ├── providers/            # Model abstraction layer
│   │   ├── granite.py        # Apache-2.0 Granite 4.0 model adapter
│   │   ├── mistral_open.py   # Mistral open adapter
│   │   ├── olmo.py           # OLMo evaluator model adapter
│   │   ├── anthropic.py      # (disabled for demo)
│   │   └── openai.py         # (disabled for demo)
│   ├── agent_simulator.py    # Multi-agent orchestration for testing
│   └── db/
│       ├── mongo_client.py   # MongoDB Atlas + Vector Search setup
│       └── aggregation.py    # Metric rollups
├── frontend/
│   ├── dashboard/            # Next.js + D3.js visualization
│   └── components/
├── configs/
│   ├── models.demo.yaml      # Apache-2.0 open-source setup (Granite + OLMo)
│   └── models.closed.yaml    # Optional closed models (Claude, GPT) for post-hack eval
└── README.md
```

## System Design

### 1. Agent Simulation
Simulates pipelines like:
```
Planner → Researcher → Writer → Evaluator
```
Each agent:
- Receives input context  
- Processes and emits new context  
- Stores both in MongoDB with embeddings

### 2. Evaluator Agent (Judge)
Uses a separate model (OLMo 2 or Mistral open) to evaluate:
- Semantic similarity (embedding-based)
- Key fact retention
- Topic drift
- Structural coherence

### 3. Storage & Indexing
MongoDB serves as the central store:
```json
{
  "handoff_id": "a1b2c3",
  "agent_from": "planner",
  "agent_to": "researcher",
  "context_sent": "...",
  "context_received": "...",
  "eval_scores": {
    "fidelity": 0.86,
    "drift": 0.11,
    "compression": 0.42
  },
  "vectors": {
    "sent": [ ... ],
    "received": [ ... ],
    "output": [ ... ]
  },
  "timestamp": "2025-10-11T08:32:00Z"
}
```

Vector indexes enable semantic search, similarity joins, and aggregation pipelines.

### 4. Dashboard
Interactive visualization:
- Agent graph (nodes = agents, edges = context flows)
- Heatmap: Context retention vs drift
- Compression–Utility tradeoff
- Diff viewer: Lost facts or misinterpreted context

## Stack

| Layer | Technology | License |
|--------|-------------|----------|
| Models (Reasoners) | Granite 4.0 (IBM) | Apache-2.0 |
| Judge Model | OLMo / Mistral open | Apache-2.0 |
| Database | MongoDB Atlas + Vector Search | Server Side Public License |
| Backend | Python + FastAPI | MIT |
| Frontend | Next.js + D3.js | MIT |
| Embeddings | Instructor-XL / GTE-Large | Apache-2.0 |

## Model Strategy

For Hackathon (fully open):
- Reasoners: granite-4.0-h-medium
- Evaluator: olmo-2-7b
- Embeddings: gte-large (or instructor-xl)

Post-hackathon (optional):
- Enable anthropic.py, openai.py, or gemini.py
- Run same evaluation pipelines and publish comparison study:  
  “Do open models preserve context as well as proprietary ones?”

## Example Evaluation Run

### Task
Agent A retrieves company financials.  
Agent B writes a summary based on A’s context.  
Evaluator scores the fidelity of information transfer.

Output Example:
```
Context Fidelity: 0.87
Relevance Drift: 0.09
Compression Efficiency: 42% token reduction
Response Utility: +12% vs no-context baseline
```

Mongo Aggregation Result:
```json
{
  "avg_fidelity": 0.84,
  "avg_drift": 0.11,
  "best_format": "JSON (schema_v2)",
  "worst_format": "Markdown (raw)"
}
```

## Setup

```bash
# Clone repo
git clone https://github.com/<yourname>/contextscope-eval.git
cd contextscope-eval

# Install dependencies
pip install -r requirements.txt

# Run MongoDB locally or connect to Atlas
export MONGO_URI="mongodb+srv://<yourcluster>"

# Launch evaluator service
python backend/app.py

# Start dashboard
cd frontend && npm install && npm run dev
```

Configurable via:
```bash
--model-config configs/models.demo.yaml
```


## Example Visualization

```
Planner ───(fidelity=0.83)──▶ Researcher ───(fidelity=0.91)──▶ Writer
                ↑                                 ↓
         drift=0.12                         drift=0.08
```

Color-coding:
- Green edges: high fidelity, low drift  
- Red edges: high drift, low fidelity  
- Hover → shows token compression stats and last context diff

## Future Work

- Cross-agent memory graph persistence  
- Self-correcting context handoffs (feedback into prompts)  
- LLM-based evaluators for causal influence between agents  
- Integrate with Braintrust / LangSmith for comparative reporting  
- Add closed-model eval post-hackathon (Claude/GPT/Gemini)  

## License

Apache-2.0 (Models)  
MIT (Code)  
All components in the demo comply with open-source licensing rules.

## Why This Wins

- Novel: Nobody measures context transmission quality between agents yet.  
- Compliant: 100% open-source; uses Apache-2.0 models (Granite, OLMo).  
- Visual: Beautiful, intuitive dashboard; perfect for live demo.  


# ContextScope Eval — Demo Scenario (Mflix Dataset)

## Objective

Demonstrate how ContextScope Eval measures and visualizes the quality of agent-to-agent context sharing using MongoDB’s sample Mflix dataset.
We’ll show how different data handoff formats (structured vs freeform) affect context fidelity, drift, and compression across multi-agent workflows.

## Overview

In this demo, two multi-agent pipelines build personalized movie recommendation systems using the Mflix dataset. Both perform the same task — generating movie recommendations for users — but use different context representations when passing information between agents.

| Pipeline | Context Format | Description |
|-----------|----------------|--------------|
| Pipeline A | JSON Schema | Agents communicate via structured JSON objects containing user profiles, movie metadata, and recommendation scores. |
| Pipeline B | Markdown Summary | Agents communicate via freeform text descriptions and natural language summaries. |

Both pipelines perform a multi-agent reasoning chain:
```
User Profiler → Content Analyzer → Recommender → Explainer → Evaluator
```

## Dataset: MongoDB Sample Mflix

Mflix is a public dataset available directly in MongoDB Atlas with multiple collections for building recommendation systems.

**Collections Used:**
- `sample_mflix.movies` - Movie catalog with metadata and embeddings
- `sample_mflix.users` - User accounts and profiles
- `sample_mflix.comments` - User reviews and ratings
- `sample_mflix.theaters` - Theater locations (optional for geo-based recommendations)

**Example Movie Document:**
```json
{
  "_id": ObjectId("573a1390f29313caabcd413b"),
  "title": "Inception",
  "year": 2010,
  "genres": ["Action", "Adventure", "Sci-Fi"],
  "directors": ["Christopher Nolan"],
  "imdb": { "rating": 8.8, "votes": 2000000 },
  "plot": "A thief who steals corporate secrets through dream-sharing technology...",
  "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
  "runtime": 148,
  "rated": "PG-13",
  "countries": ["USA", "UK"],
  "languages": ["English"],
  "plot_embedding": [0.023, -0.145, 0.089, ...],
  "tomatoes": {
    "viewer": { "rating": 4.3, "numReviews": 156789 },
    "critic": { "rating": 4.1, "numReviews": 285 }
  }
}
```

**Example User Document:**
```json
{
  "_id": ObjectId("59b99db4cfa9a34dcd7885b6"),
  "name": "Sarah Chen",
  "email": "sarah.chen@example.com",
  "preferences": {
    "favorite_genres": ["Sci-Fi", "Thriller", "Drama"],
    "disliked_genres": ["Horror"],
    "preferred_decades": ["2000s", "2010s"]
  }
}
```

**Example Comment/Rating Document:**
```json
{
  "_id": ObjectId("5a9427648b0beebeb69579e7"),
  "movie_id": ObjectId("573a1390f29313caabcd413b"),
  "user_id": ObjectId("59b99db4cfa9a34dcd7885b6"),
  "name": "Sarah Chen",
  "email": "sarah.chen@example.com",
  "text": "Mind-bending and visually stunning. Nolan at his best!",
  "date": "2024-08-15T14:32:00Z"
}
```

## Task Definition

Both pipelines receive the same system task:

**Task:** "Generate personalized movie recommendations for a user based on their viewing history, preferences, and similar user behavior."

**Input:** User ID from `sample_mflix.users`

**Output:** Top 5 movie recommendations with explanations

## Multi-Agent Recommendation Pipeline

Each agent in the pipeline contributes to the recommendation process:

| Agent | Role | Input | Output | Purpose |
|--------|------|-------|--------|---------|
| **User Profiler** | Profile Analysis | User ID | User preference summary, watch history, genre affinities | Extracts and analyzes user behavior patterns |
| **Content Analyzer** | Movie Feature Extraction | User profile + Movie catalog | Candidate movie features and themes | Identifies movies matching user preferences |
| **Recommender** | Ranking & Scoring | User profile + Candidate movies | Scored recommendations with relevance scores | Generates personalized ranking |
| **Explainer** | Justification Generation | Recommendations + User profile | Natural language explanations | Provides reasoning for each recommendation |
| **Evaluator** | Context Quality Judge | All agent outputs | Fidelity, drift, and compression metrics | Measures context transmission quality |

## Pipeline A — Structured JSON Context

### Agent 1: User Profiler Output (A)
```json
{
  "user_id": "59b99db4cfa9a34dcd7885b6",
  "profile": {
    "name": "Sarah Chen",
    "top_genres": [
      { "genre": "Sci-Fi", "affinity": 0.92 },
      { "genre": "Thriller", "affinity": 0.85 },
      { "genre": "Drama", "affinity": 0.78 }
    ],
    "director_preferences": [
      { "director": "Christopher Nolan", "avg_rating": 4.5 },
      { "director": "Denis Villeneuve", "avg_rating": 4.3 }
    ],
    "watch_history": [
      { "title": "Interstellar", "rating": 5, "date": "2024-09-12" },
      { "title": "Arrival", "rating": 4, "date": "2024-09-05" },
      { "title": "Blade Runner 2049", "rating": 5, "date": "2024-08-28" }
    ],
    "avg_runtime_preference": 135,
    "decade_preference": ["2010s", "2020s"],
    "language_preference": ["English"]
  },
  "context_metadata": {
    "tokens": 245,
    "embedding_dim": 768
  }
}
```

### Agent 2: Content Analyzer Output (A)
```json
{
  "user_profile_summary": {
    "primary_interests": ["Sci-Fi", "Thriller", "Christopher Nolan"],
    "profile_embedding": [0.123, -0.456, ...]
  },
  "candidate_movies": [
    {
      "movie_id": "573a1390f29313caabcd4150",
      "title": "Tenet",
      "year": 2020,
      "genres": ["Action", "Sci-Fi", "Thriller"],
      "director": "Christopher Nolan",
      "imdb_rating": 7.3,
      "similarity_score": 0.94,
      "match_reasons": ["director_match", "genre_overlap", "recent_release"]
    },
    {
      "movie_id": "573a1390f29313caabcd4151",
      "title": "Dune",
      "year": 2021,
      "genres": ["Adventure", "Drama", "Sci-Fi"],
      "director": "Denis Villeneuve",
      "imdb_rating": 8.0,
      "similarity_score": 0.89,
      "match_reasons": ["director_match", "genre_overlap", "high_rating"]
    }
  ],
  "context_metadata": {
    "tokens": 428,
    "candidates_analyzed": 1523,
    "vector_search_time_ms": 45
  }
}
```

### Agent 3: Recommender Output (A)
```json
{
  "recommendations": [
    {
      "rank": 1,
      "movie_id": "573a1390f29313caabcd4151",
      "title": "Dune",
      "confidence_score": 0.91,
      "relevance_factors": {
        "genre_match": 0.95,
        "director_match": 0.88,
        "rating_quality": 0.89,
        "recency": 0.92
      }
    },
    {
      "rank": 2,
      "movie_id": "573a1390f29313caabcd4150",
      "title": "Tenet",
      "confidence_score": 0.88,
      "relevance_factors": {
        "genre_match": 0.92,
        "director_match": 1.0,
        "rating_quality": 0.73,
        "recency": 0.95
      }
    }
  ],
  "context_metadata": {
    "tokens": 312,
    "ranking_algorithm": "weighted_hybrid",
    "total_candidates": 5
  }
}
```

### Agent 4: Explainer Output (A)
```json
{
  "recommendations_with_explanations": [
    {
      "rank": 1,
      "title": "Dune",
      "explanation": "Based on your love for Denis Villeneuve's work (you rated Arrival 4/5 and Blade Runner 2049 5/5), you'll likely enjoy Dune. It combines epic sci-fi world-building with philosophical themes similar to Interstellar, which you rated 5/5.",
      "key_appeal_points": [
        "Director: Denis Villeneuve (matches your top preferences)",
        "Genres: Sci-Fi, Adventure, Drama (92% match)",
        "Similar thematic depth to your favorite films",
        "Recent release (2021), critically acclaimed"
      ]
    },
    {
      "rank": 2,
      "title": "Tenet",
      "explanation": "As a Christopher Nolan fan (your #1 director preference), Tenet offers his signature mind-bending narrative style. Combines action with complex sci-fi concepts about time manipulation.",
      "key_appeal_points": [
        "Director: Christopher Nolan (your top director, 4.5 avg)",
        "Genres: Sci-Fi, Thriller, Action (88% match)",
        "Complex narrative structure you seem to prefer",
        "Recent release (2020)"
      ]
    }
  ],
  "context_metadata": {
    "tokens": 389,
    "explanation_style": "personalized_with_references"
  }
}
```

### Evaluator Output (A)
```json
{
  "handoff_scores": [
    {
      "from": "User Profiler",
      "to": "Content Analyzer",
      "fidelity": 0.93,
      "drift": 0.06,
      "compression_efficiency": 0.42,
      "key_info_preserved": ["genre_preferences", "director_preferences", "watch_history"]
    },
    {
      "from": "Content Analyzer",
      "to": "Recommender",
      "fidelity": 0.91,
      "drift": 0.08,
      "compression_efficiency": 0.48,
      "key_info_preserved": ["candidate_movies", "similarity_scores", "match_reasons"]
    },
    {
      "from": "Recommender",
      "to": "Explainer",
      "fidelity": 0.89,
      "drift": 0.10,
      "compression_efficiency": 0.51,
      "key_info_preserved": ["rankings", "confidence_scores", "relevance_factors"]
    }
  ],
  "overall_pipeline_score": {
    "avg_fidelity": 0.91,
    "avg_drift": 0.08,
    "total_compression": 0.47,
    "end_to_end_fidelity": 0.87
  }
}
```

## Pipeline B — Freeform Markdown Context

### Agent 1: User Profiler Output (B)
```markdown
# User Profile: Sarah Chen

Sarah is a science fiction enthusiast who particularly enjoys thought-provoking films with complex narratives.

## Favorite Directors
- Christopher Nolan (especially Interstellar - rated 5/5)
- Denis Villeneuve (loved Arrival and Blade Runner 2049)

## Genre Preferences
Strongly prefers: Sci-Fi, Thriller, Drama
Avoids: Horror movies

## Recent Activity
- Recently watched Interstellar (5 stars)
- Enjoyed Arrival (4 stars) 
- Loved Blade Runner 2049 (5 stars)

Sarah tends to prefer movies around 2 hours long and likes recent releases from the 2010s and 2020s.
```

### Agent 2: Content Analyzer Output (B)
```markdown
# Movie Recommendations Analysis for Sarah

Based on Sarah's profile, I found several great matches in our catalog:

## Top Candidates

**Dune (2021)** by Denis Villeneuve looks perfect. It's an epic sci-fi adventure that combines stunning visuals with deep philosophical themes. Since Sarah rated both Arrival and Blade Runner 2049 highly, she'll love this.

**Tenet (2020)** is another Christopher Nolan mind-bender about time manipulation. Given her 5-star rating for Interstellar, this should be a great fit.

Other possibilities include The Martian, Ex Machina, and Annihilation - all recent sci-fi films with strong ratings.
```

### Agent 3: Recommender Output (B)
```markdown
# Top 5 Recommendations for Sarah

1. **Dune** - Highest confidence. Denis Villeneuve film, epic sci-fi, recent.
2. **Tenet** - Christopher Nolan's latest, complex thriller.
3. **The Martian** - Sci-fi with realistic science, engaging story.
4. **Ex Machina** - Thoughtful AI thriller, indie gem.
5. **Annihilation** - Mind-bending sci-fi with strong visuals.

All of these match Sarah's preference for intelligent sci-fi films.
```

### Agent 4: Explainer Output (B)
```markdown
# Your Personalized Movie Recommendations

Hi Sarah! Based on your viewing history, here are my top picks:

**1. Dune**
You'll love this since you enjoyed other Denis Villeneuve films. It has the epic scope of Interstellar combined with the visual mastery you loved in Blade Runner 2049.

**2. Tenet**
Another Christopher Nolan film with mind-bending concepts. If you liked Interstellar's complexity, this is a must-watch.

These recommendations are tailored to your love of thoughtful sci-fi and your favorite directors.
```

### Evaluator Output (B)
```json
{
  "handoff_scores": [
    {
      "from": "User Profiler",
      "to": "Content Analyzer",
      "fidelity": 0.71,
      "drift": 0.22,
      "compression_efficiency": 0.58,
      "info_lost": ["specific_ratings", "watch_dates", "quantitative_metrics"]
    },
    {
      "from": "Content Analyzer",
      "to": "Recommender",
      "fidelity": 0.65,
      "drift": 0.28,
      "compression_efficiency": 0.61,
      "info_lost": ["similarity_scores", "match_reasons", "specific_metrics"]
    },
    {
      "from": "Recommender",
      "to": "Explainer",
      "fidelity": 0.68,
      "drift": 0.25,
      "compression_efficiency": 0.55,
      "info_lost": ["confidence_scores", "ranking_justifications"]
    }
  ],
  "overall_pipeline_score": {
    "avg_fidelity": 0.68,
    "avg_drift": 0.25,
    "total_compression": 0.58,
    "end_to_end_fidelity": 0.52
  }
}
```

## Evaluation Metrics Comparison

| Metric | Description | Pipeline A (JSON) | Pipeline B (Markdown) |
|---------|--------------|-------------------|----------------------|
| **End-to-End Fidelity** | Overall information preservation from User Profiler → Explainer | 0.87 | 0.52 |
| **Average Fidelity** | Mean fidelity across all agent handoffs | 0.91 | 0.68 |
| **Average Drift** | Mean semantic deviation across handoffs | 0.08 | 0.25 |
| **Compression Efficiency** | Token reduction while preserving information | 47% | 58% |
| **Recommendation Quality** | User satisfaction with recommendations (simulated) | 4.2/5.0 | 3.1/5.0 |
| **Explainability Score** | Quality of recommendation justifications | 0.89 | 0.64 |

## Dashboard Visualization

**Multi-Agent Context Flow Graph:**
```
Pipeline A (JSON) - High Fidelity Chain
User Profiler ──(0.93)──▶ Content Analyzer ──(0.91)──▶ Recommender ──(0.89)──▶ Explainer
     ↓                           ↓                          ↓                    ↓
  drift=0.06                 drift=0.08                drift=0.10          drift=0.11

Pipeline B (Markdown) - Information Loss Chain
User Profiler ──(0.71)──▶ Content Analyzer ──(0.65)──▶ Recommender ──(0.68)──▶ Explainer
     ↓                           ↓                          ↓                    ↓
  drift=0.22                 drift=0.28                drift=0.25          drift=0.29
```

**Context Fidelity Heatmap:**
| Pipeline | User Profiler → Content | Content → Recommender | Recommender → Explainer | Overall |
|----------|-------------------------|----------------------|-------------------------|---------|
| JSON (A) | ██████████ 93% | █████████░ 91% | █████████░ 89% | █████████░ 87% |
| Markdown (B) | ███████░░░ 71% | ██████░░░░ 65% | ███████░░░ 68% | █████░░░░░ 52% |

**Drift Analysis:**
| Pipeline | Avg Drift | Peak Drift | Cumulative Loss |
|----------|-----------|-----------|-----------------|
| JSON (A) | 8% | 11% | 13% |
| Markdown (B) | 25% | 29% | 48% |

## Interpretation

### Key Findings

1. **Structured JSON Context Preserves 67% More Information**
   - End-to-end fidelity: 0.87 (JSON) vs 0.52 (Markdown)
   - Critical user preferences and movie metadata remain intact through the full pipeline

2. **Markdown Compression Comes at a High Cost**
   - While Markdown achieves 11% better compression (58% vs 47%), it loses nearly half of the original context by the final agent
   - Quantitative data (ratings, scores, dates) gets lost in natural language descriptions

3. **Drift Compounds Through Multi-Agent Chains**
   - JSON: Each handoff adds ~6-10% drift
   - Markdown: Each handoff adds ~22-29% drift
   - By the 4th agent, Markdown pipeline has 3× higher drift

4. **Recommendation Quality Correlates with Context Fidelity**
   - JSON pipeline produces higher quality recommendations (4.2/5 vs 3.1/5)
   - Better explanations (0.89 vs 0.64) due to preserved context about user preferences and movie features

### MongoDB-Specific Insights

**Vector Search Performance:**
- `plot_embedding` field enables semantic similarity matching
- Structured JSON preserves embedding references better than natural language
- Atlas Vector Search query time: ~45ms for 1500+ movie documents

**Multi-Collection Joins:**
- `users` + `comments` + `movies` collections work together
- JSON format maintains referential integrity across collections
- Markdown format loses ObjectId references, hindering data traceability

## Key Takeaways for the Judges

1. **Novel Evaluation Framework**: ContextScope quantifies agent-to-agent context transmission quality — a previously unmeasured dimension of multi-agent systems.

2. **Real-World Application**: Movie recommendation system demonstrates practical value using MongoDB's Mflix dataset with actual user profiles, ratings, and movie metadata.

3. **Data Format Impact**: Structured context leads to 67% better information preservation and 35% higher recommendation quality compared to freeform text.

4. **MongoDB Atlas Integration**: 
   - Leverages Vector Search for semantic matching
   - Uses multiple collections (users, movies, comments) to build realistic agent workflows
   - No fine-tuning or custom RAG required — works with sample data out of the box

5. **Scalable Architecture**: Framework can evaluate any multi-agent pipeline, making it valuable for enterprises building agent-based systems.

## How to Reproduce

### 1. Set Up MongoDB Atlas
```bash
# Load sample Mflix data (includes users, movies, comments)
atlas clusters loadSampleData <clusterName>

# Create vector search index on plot_embedding field
atlas clusters search indexes create \
  --clusterName <clusterName> \
  --indexName plot_embedding_index \
  --db sample_mflix \
  --collection movies
```

### 2. Configure Environment
```bash
# Set MongoDB connection string
export MONGO_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net"

# Optional: Set API keys for open-source models
export GRANITE_API_KEY="your-key"
export OLMO_API_KEY="your-key"
```

### 3. Run the Recommendation Demo
```bash
# Start backend evaluator service
cd backend
python app.py --task movie_recommendations --user-id "59b99db4cfa9a34dcd7885b6"

# The system will:
# 1. Run Pipeline A (JSON) and Pipeline B (Markdown) in parallel
# 2. Generate recommendations using both formats
# 3. Evaluate context fidelity at each agent handoff
# 4. Store results in MongoDB with embeddings
```

### 4. Launch Dashboard
```bash
# Start frontend visualization
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

### 5. View Results
- **Agent Flow Graph**: Visualize context transmission quality
- **Fidelity Scores**: See per-handoff metrics
- **Recommendation Comparison**: Compare Pipeline A vs B outputs
- **Context Diff Viewer**: Inspect what information was lost at each step

## Extensions & Future Work

### Immediate Extensions (Post-Demo)
1. **Collaborative Filtering Agent**: Add user similarity analysis using `comments` collection
2. **Temporal Context Test**: Track how recommendation quality degrades over time as user preferences drift
3. **Multi-Hop Evaluation**: Extend pipeline to 6-8 agents and measure cumulative context loss
4. **Geographic Recommendations**: Use `theaters` collection for location-based suggestions

### Research Opportunities
1. **Self-Healing Context**: Automatically detect drift and re-inject lost information
2. **Optimal Format Selection**: ML model that predicts best context format per agent type
3. **Cross-Model Comparison**: Compare context preservation across Granite, OLMo, Mistral, and closed models
4. **Enterprise Benchmark**: Create standardized test suite for evaluating production agent systems

### MongoDB Advanced Features
1. **Change Streams**: Real-time context monitoring as agents communicate
2. **Aggregation Pipelines**: Complex metric rollups and trend analysis
3. **Time Series Collections**: Track context fidelity metrics over time
4. **Atlas Search**: Full-text search on agent outputs for qualitative analysis



