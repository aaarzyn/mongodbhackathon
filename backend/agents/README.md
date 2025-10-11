# Agent System Documentation

## Overview

The agent system implements a multi-agent pipeline for movie recommendations with context evaluation. Each agent processes input context and produces output context that can be measured for fidelity and drift.

## Architecture

```
User Profiler → Content Analyzer → Recommender → Explainer
       ↓                ↓               ↓            ↓
   [Context]        [Context]       [Context]   [Context]
       ↓                ↓               ↓            ↓
   Evaluator    →   Evaluator   →  Evaluator  → Evaluator
```

## Base Classes

### Agent (Abstract Base Class)

All agents inherit from the `Agent` base class:

```python
from backend.agents.base import Agent, AgentContext, ContextFormat

class MyAgent(Agent):
    def __init__(self, context_format=ContextFormat.JSON):
        super().__init__("MyAgent", context_format)
    
    def process(self, input_context: Optional[AgentContext] = None) -> AgentOutput:
        # Your agent logic here
        pass
```

### AgentContext

Context passed between agents:

```python
{
    "agent_name": "UserProfilerAgent",
    "format": "json",  # or "markdown"
    "data": {...},  # The actual context data
    "timestamp": "2025-10-11T12:00:00Z",
    "tokens": 245,
    "metadata": {}
}
```

### AgentOutput

Output from an agent:

```python
{
    "context": AgentContext,
    "execution_time_ms": 125.5,
    "success": True,
    "error_message": None
}
```

## Implemented Agents

### 1. User Profiler Agent

**Purpose:** Analyzes user behavior and extracts preferences from viewing history.

**Input:** User ID or email

**Output:** Comprehensive user profile including:
- Genre affinities with scores
- Favorite directors and actors
- Viewing patterns (runtime preferences, decades)
- Recent watch history

**Supported Formats:**
- **JSON**: Structured profile with all metrics and scores
- **Markdown**: Human-readable narrative format

**Example Usage:**

```python
from backend.agents import UserProfilerAgent
from backend.agents.base import ContextFormat
from backend.services import MflixService
from backend.db import get_mongo_client

# Setup
client = get_mongo_client()
service = MflixService(client)

# Create agent
profiler = UserProfilerAgent(service, context_format=ContextFormat.JSON)

# Profile a user
output = profiler.process_user("user@example.com")

if output.success:
    profile = output.context.data
    print(f"User: {profile['name']}")
    print(f"Top genres: {[g['genre'] for g in profile['genre_affinities'][:3]]}")
    print(f"Execution time: {output.execution_time_ms}ms")
```

**Key Methods:**

- `process_user(email)` - Profile user by email
- `_compute_genre_affinities(movies)` - Calculate genre preferences
- `_extract_director_preferences(movies)` - Find favorite directors
- `_extract_actor_preferences(movies)` - Find favorite actors
- `_analyze_viewing_patterns(comments, movies)` - Extract viewing habits

**Performance:**
- Typical execution: 2-5 seconds
- Token count (JSON): ~100-500 tokens
- Token count (Markdown): ~15-100 tokens
- Compression ratio: ~80-85% (Markdown vs JSON)

## Context Formats

### JSON Format

Structured format that preserves all data with full precision:

**Advantages:**
- Complete information preservation
- Easy to parse programmatically
- Maintains quantitative data (scores, counts, ratings)
- Better for downstream agent processing

**Disadvantages:**
- More verbose (higher token count)
- Less human-readable
- Can include redundant structure

**Example:**
```json
{
  "user_id": "123",
  "name": "John Doe",
  "genre_affinities": [
    {
      "genre": "Sci-Fi",
      "affinity": 0.85,
      "count": 17
    }
  ],
  "director_preferences": [
    {
      "name": "Christopher Nolan",
      "movie_count": 5,
      "avg_rating": 8.4
    }
  ]
}
```

### Markdown Format

Natural language format for human-readable output:

**Advantages:**
- Highly compressed (80-85% reduction)
- Human-readable
- Easier to understand intent
- Good for explanation agents

**Disadvantages:**
- Loses quantitative precision
- Harder to parse programmatically
- Semantic information may drift
- Missing structured relationships

**Example:**
```markdown
# User Profile: John Doe

## Genre Preferences
- **Sci-Fi**: 85% affinity (17 movies)
- **Thriller**: 72% affinity (12 movies)

## Favorite Directors
- **Christopher Nolan**: 5 movies, avg rating 8.4
```

## Testing

### Run All Agent Tests

```bash
# Test User Profiler
python test_user_profiler.py

# Test with different formats
python -c "
from backend.agents import UserProfilerAgent
from backend.agents.base import ContextFormat
from backend.services import MflixService
from backend.db import get_mongo_client

client = get_mongo_client()
service = MflixService(client)

# Test JSON format
json_agent = UserProfilerAgent(service, ContextFormat.JSON)
json_out = json_agent.process_user('user@example.com')
print(f'JSON tokens: {json_out.context.tokens}')

# Test Markdown format
md_agent = UserProfilerAgent(service, ContextFormat.MARKDOWN)
md_out = md_agent.process_user('user@example.com')
print(f'Markdown tokens: {md_out.context.tokens}')
print(f'Compression: {md_out.context.tokens / json_out.context.tokens:.1%}')
"
```

## Next Agents to Implement

### 2. Content Analyzer Agent (TODO)

- **Input**: User profile from User Profiler
- **Output**: Candidate movies with match scores
- **Uses**: MongoDB Vector Search on `plot_embedding` field
- **Key logic**: Semantic similarity matching

### 3. Recommender Agent (TODO)

- **Input**: User profile + Candidate movies
- **Output**: Ranked recommendations with confidence scores
- **Key logic**: Weighted scoring algorithm (genre match, director match, ratings)

### 4. Explainer Agent (TODO)

- **Input**: User profile + Recommendations
- **Output**: Natural language explanations for each recommendation
- **Key logic**: Template-based or LLM-generated justifications

### 5. Evaluator Agent (TODO)

- **Input**: All agent outputs in the pipeline
- **Output**: Context fidelity, drift, and compression metrics
- **Key logic**: Semantic similarity, information preservation analysis

## Development Guidelines

### Adding a New Agent

1. **Inherit from Agent base class**
2. **Implement `process()` method**
3. **Support both JSON and Markdown formats**
4. **Add comprehensive docstrings**
5. **Create a test script**
6. **Document in this README**

### Best Practices

- Keep agents focused on a single responsibility
- Use type hints throughout
- Log important steps and timing
- Handle errors gracefully
- Return structured `AgentOutput` objects
- Estimate token counts for context
- Support both output formats

### Error Handling

```python
try:
    # Agent logic
    result = do_something()
    context = self._create_context(data=result)
    return AgentOutput(context=context, execution_time_ms=time_ms, success=True)
except Exception as e:
    logger.error(f"Agent failed: {str(e)}")
    return AgentOutput(
        context=self._create_context(data={}),
        execution_time_ms=time_ms,
        success=False,
        error_message=str(e)
    )
```

## Performance Benchmarks

| Agent | Avg Time | JSON Tokens | Markdown Tokens | Compression |
|-------|----------|-------------|-----------------|-------------|
| User Profiler | 2-5s | 100-500 | 15-100 | 80-85% |
| Content Analyzer | TBD | TBD | TBD | TBD |
| Recommender | TBD | TBD | TBD | TBD |
| Explainer | TBD | TBD | TBD | TBD |

## References

- **Base Classes**: `backend/agents/base.py`
- **User Profiler**: `backend/agents/user_profiler.py`
- **Test Script**: `test_user_profiler.py`
- **Project Spec**: `PROJECT.md`

