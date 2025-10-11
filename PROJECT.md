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

In this demo, two multi-agent pipelines perform the same task — summarizing movies from the Mflix dataset — but use different context representations when passing information between agents.

| Pipeline | Context Format | Description |
|-----------|----------------|--------------|
| Pipeline A | JSON Schema | Agents communicate via structured JSON objects containing movie metadata. |
| Pipeline B | Markdown Summary | Agents communicate via freeform text summaries in Markdown. |

Both pipelines perform a reasoning chain:
```
Researcher → Summarizer → Evaluator
```

## Dataset: MongoDB Sample Mflix

Mflix is a public dataset available directly in MongoDB Atlas.
It contains movie documents with embedded metadata and pre-computed embeddings.

**Collection:** `sample_mflix.movies`

**Example Document:**
```json
{
  "title": "Inception",
  "year": 2010,
  "genres": ["Action", "Adventure", "Sci-Fi"],
  "directors": ["Christopher Nolan"],
  "imdb": { "rating": 8.8, "votes": 2000000 },
  "plot": "A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO.",
  "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
  "language": ["English"],
  "countries": ["USA", "UK"]
}
```

## Task Definition

Both pipelines receive the same system task:

**Task:** “Summarize the defining characteristics of Christopher Nolan’s top-rated films and describe how they connect thematically.”

Each agent contributes differently:

| Agent | Role | Action |
|--------|------|--------|
| Researcher | Data retrieval | Queries MongoDB for top 5 Christopher Nolan films by IMDb rating. Returns results in chosen format (JSON or Markdown). |
| Summarizer | Reasoning & synthesis | Reads context from the Researcher and produces a written summary. |
| Evaluator | Judge model | Computes context fidelity, drift, and compression efficiency between agents. |

## Pipeline A — Structured JSON Context

**Researcher Output (A):**
```json
[
  {
    "title": "Inception",
    "year": 2010,
    "rating": 8.8,
    "themes": ["dreams", "reality", "identity"]
  },
  {
    "title": "Interstellar",
    "year": 2014,
    "rating": 8.6,
    "themes": ["love", "time", "sacrifice"]
  },
  {
    "title": "The Dark Knight",
    "year": 2008,
    "rating": 9.0,
    "themes": ["chaos", "justice", "dual identity"]
  }
]
```

**Summarizer Output (A):**
> Christopher Nolan’s top-rated films explore the boundaries of perception and moral conflict. Across Inception, Interstellar, and The Dark Knight, his characters confront time, reality, and the burden of responsibility.

**Evaluator Output (A):**
```json
{
  "fidelity": 0.91,
  "drift": 0.08,
  "compression_efficiency": 0.45
}
```

## Pipeline B — Freeform Markdown Context

**Researcher Output (B):**
```
# Top-Rated Christopher Nolan Movies

- Inception (2010): Explores dreams and reality.
- Interstellar (2014): Themes of time, love, and sacrifice.
- The Dark Knight (2008): Chaos, justice, and moral complexity.
```

**Summarizer Output (B):**
> Nolan’s movies are imaginative and emotional, dealing with human struggles and technology.

**Evaluator Output (B):**
```json
{
  "fidelity": 0.68,
  "drift": 0.24,
  "compression_efficiency": 0.51
}
```

## Evaluation Metrics

| Metric | Description | Result (JSON) | Result (Markdown) |
|---------|--------------|---------------|-------------------|
| Context Fidelity | How well Agent B retained Agent A’s key facts. | 0.91 | 0.68 |
| Relevance Drift | Degree of deviation from original facts. | 0.08 | 0.24 |
| Compression Efficiency | Token reduction from A → B. | 45% | 51% |
| Utility Gain | Relative improvement in downstream task accuracy. | +12% | +3% |

## Dashboard Visualization

**Context Graph:**
```
Pipeline A (JSON)
Researcher ── fidelity=0.91 ──▶ Summarizer

Pipeline B (Markdown)
Researcher ── fidelity=0.68 ──▶ Summarizer
```

**Heatmap:**
| Format | Fidelity | Drift | Compression |
|---------|-----------|-------|-------------|
| JSON | ██████████ 91% | ░░░░░░░░ 8% | 45% |
| Markdown | ██████░░░░ 68% | ████░░░░░░ 24% | 51% |

## Interpretation

- Structured (JSON) handoffs preserve context significantly better than freeform (Markdown) formats.
- Even though Markdown compresses more aggressively, it loses semantic fidelity.
- ContextScope makes this tradeoff measurable and visible — demonstrating how agent communication design directly affects reasoning quality.

## Key Takeaways for the Judges

1. ContextScope quantifies agent-to-agent understanding.
2. It reveals which data formats or compression methods produce the most faithful multi-agent reasoning.
3. Using MongoDB’s vector search and Atlas data, it shows this live — no fine-tuning or RAG required.
4. The result: Structured context leads to 34% higher fidelity and 3× lower drift.

## How to Reproduce

1. Deploy MongoDB Atlas sample data:
   ```bash
   atlas clusters loadSampleData <clusterName>
   ```
2. Connect via environment variable:
   ```bash
   export MONGO_URI="mongodb+srv://<your-cluster>"
   ```
3. Run the demo:
   ```bash
   python backend/app.py --task demo_mflix
   ```
4. Open the dashboard at:
   ```
   http://localhost:3000
   ```
5. View fidelity, drift, and compression results in real time.

## Extensions (Optional)

- Add a Temporal Drift Test: Update movie ratings and measure which format reflects changes correctly.
- Introduce a Reviewer Agent to simulate multi-hop communication loss.
- Swap Granite for Mistral open to compare reasoning behavior across open models.



