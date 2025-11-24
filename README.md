# DatasetSmith Platform

**From Research Papers to Production-Ready Datasets in Minutes**

An end-to-end AI-powered platform revolutionizing ML research workflows by seamlessly connecting paper analysis, dataset generation, and experimental prototyping.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MongoDB Atlas](https://img.shields.io/badge/Database-MongoDB%20Atlas-green)](https://www.mongodb.com/atlas)
[![Powered by Tavily](https://img.shields.io/badge/Powered%20by-Tavily-orange)](https://tavily.com)
[![LastMile AI](https://img.shields.io/badge/MCP-LastMile%20AI-purple)](https://lastmileai.dev)

---

## Overview

DatasetSmith solves a critical problem in ML research: the weeks-long gap between reading a paper and having a working dataset to reproduce its results.

**The Platform:**
1. Discovers and analyzes ML papers using Tavily's advanced search
2. Extracts dataset requirements using LLM-powered analysis
3. Generates production-ready datasets with license-clean images
4. Orchestrates workflows through LastMile AI's MCP framework
5. Stores and searches everything using MongoDB Atlas with vector search

**Result:** Researchers go from paper discovery to working prototype in under 30 minutes.

---

## Prize Category Alignment

### Overall: Best AI Agent with Real-World Usability
- Addresses reproducibility crisis in ML research
- Daily workflow integration via ChatGPT/Claude/Cursor
- Production-ready with Dagster orchestration
- 10x faster research-to-prototype workflow

### MongoDB: Best Use of MongoDB Atlas
- Vector Search for semantic discovery
- Complex aggregation pipelines
- Change Streams for real-time updates
- Flexible schema for multi-modal data

### Tavily: Best Use of Tavily API
- Advanced search parameters
- Multi-modal search (papers + images)
- Domain-specific optimization
- License-clean content filtering

### LastMile AI: Best MCP Agent Project
- End-to-end MCP architecture
- Production deployment via mcp-agent
- Daily workflow integration
- Multiple MCP tools exposed

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- API Keys: Tavily, OpenAI, VoyageAI

### Installation

```bash
git clone https://github.com/exploring-curiosity/OpenBenchPublisher.git
cd OpenBenchPublisher

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup environment
uv venv
source .venv/bin/activate
uv sync

# Install frontend
cd web-ui-next && npm install && cd ..

# Install Paper Analyser
cd obp-paper-analyser && pip install -r requirements.txt && cd ..

# Configure
cp .env.example .env
# Edit .env with your API keys
```

### Start All Services

```bash
./start.sh
```

Access at:
- Paper Analyser: http://localhost:8001
- Backend API: http://localhost:8000
- Dagster UI: http://localhost:3000
- Frontend: http://localhost:3001

### Stop All Services

```bash
./stop.sh
```

---

## MongoDB Atlas Integration

### Vector Search Implementation

**Collections:**
- `papers` - Research papers with embeddings
- `claims` - Extracted claims with embeddings
- `assets` - Images with CLIP embeddings
- `datasets` - Dataset manifests
- `runs` - Pipeline execution history

**Vector Indexes:**
```javascript
// Papers collection
{
  "fields": [{
    "type": "vector",
    "path": "embed",
    "numDimensions": 384,
    "similarity": "cosine"
  }]
}
```

**Semantic Search:**
```python
pipeline = [
    {
        "$vectorSearch": {
            "index": "paper_vector_index",
            "path": "embed",
            "queryVector": query_embed,
            "numCandidates": 100,
            "limit": 10
        }
    },
    {
        "$project": {
            "title": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }
]
```

### Aggregation Pipelines

**Dataset Statistics:**
```python
pipeline = [
    {"$match": {"dataset_id": ObjectId(dataset_id)}},
    {
        "$facet": {
            "class_distribution": [
                {"$group": {
                    "_id": "$class",
                    "count": {"$sum": 1}
                }}
            ],
            "size_stats": [
                {"$group": {
                    "_id": None,
                    "avg_width": {"$avg": "$width"},
                    "avg_height": {"$avg": "$height"}
                }}
            ]
        }
    }
]
```

### Change Streams

**Real-Time Progress:**
```python
pipeline = [
    {
        "$match": {
            "operationType": {"$in": ["insert", "update"]},
            "fullDocument.request_id": request_id
        }
    }
]

with collection.watch(pipeline) as stream:
    for change in stream:
        notify_frontend(change)
```

---

## Tavily API Integration

### Advanced Paper Discovery

**Full Parameter Usage:**
```python
response = client.search(
    query="depth estimation transformers",
    search_depth="advanced",
    topic="general",
    time_range="week",
    max_results=20,
    include_domains=["arxiv.org", "openaccess.thecvf.com"],
    exclude_domains=["medium.com"],
    include_raw_content=True,
    include_images=False,
    include_answer=True
)
```

### License-Clean Image Search

**CC-BY Filtering:**
```python
response = client.search(
    query=f"{class_name} high quality photo",
    search_depth="advanced",
    max_results=20,
    include_domains=[
        "commons.wikimedia.org",
        "unsplash.com",
        "pexels.com"
    ],
    include_images=True,
    include_image_descriptions=True
)
```

### Multi-Stage Search Strategy

**Comprehensive Coverage:**
1. Primary search with exact class name
2. Synonym search for diversity
3. Context-specific searches
4. Deduplication via MongoDB vector search
5. Quality selection based on resolution

---

## LastMile AI MCP Integration

### MCP Tools Exposed

**build_dataset_slice:**
```python
@app.async_tool(name="build_dataset_slice")
async def build_dataset_slice(
    classes: List[str],
    total: int = 100,
    min_size: int = 256,
    license_filter: str = "CC-BY",
    app_ctx: Optional[AppContext] = None
) -> str:
    """Build license-clean dataset using Tavily + MongoDB"""
    # Implementation
```

**list_datasets:**
```python
@app.tool(name="list_datasets")
async def list_datasets(app_ctx: Optional[AppContext] = None) -> str:
    """List all datasets from MongoDB Atlas"""
    # Implementation
```

**export_dataset:**
```python
@app.tool(name="export_dataset")
async def export_dataset_tool(
    dataset_id: str,
    app_ctx: Optional[AppContext] = None
) -> str:
    """Export dataset as organized ZIP"""
    # Implementation
```

### Deployment

**To LastMile Cloud:**
```bash
uvx mcp-agent deploy
```

**Local Development:**
```bash
uv run mcp_stdio_server.py
```

### Client Integration

**ChatGPT:**
```json
{
  "mcpServers": {
    "datasetsmith": {
      "type": "lastmile",
      "appId": "app_xxx",
      "apiKey": "your_key"
    }
  }
}
```

**Claude Desktop:**
```json
{
  "mcpServers": {
    "datasetsmith": {
      "command": "uv",
      "args": ["run", "mcp_stdio_server.py"],
      "cwd": "/path/to/DatasetSmith"
    }
  }
}
```

---

## Technology Stack

**Backend:**
- Python 3.11+ with async/await
- FastAPI for REST APIs
- Dagster for orchestration
- uv for package management

**Frontend:**
- Next.js 15 (App Router)
- React 19 + TypeScript
- TailwindCSS
- Lucide Icons

**AI & Search:**
- Tavily API (paper + image search)
- OpenAI GPT-4o-mini (analysis)
- VoyageAI (embeddings)
- LastMile AI (MCP deployment)

**Data & Storage:**
- MongoDB Atlas (database + vector search)
- Pillow + ImageHash (image processing)
- sentence-transformers (text embeddings)

---

## Real-World Usage

### Daily Workflow

1. **Morning:** Check new papers via ChatGPT
   ```
   "Find yesterday's cs.CV papers on depth estimation"
   ```

2. **Analysis:** Extract dataset requirements
   ```
   "Analyze the top paper and tell me what dataset I need"
   ```

3. **Generation:** Build dataset
   ```
   "Build that dataset with 100 images"
   ```

4. **Prototyping:** Download and experiment
   ```
   "Export the dataset as ZIP"
   ```

**Time Saved:** 2-3 weeks reduced to 30 minutes

### Production Features

- Health check endpoints
- Comprehensive logging
- Error handling with retries
- MongoDB connection pooling
- Async/await throughout
- Type hints everywhere
- Dagster monitoring
- Real-time progress tracking

---

## API Documentation

### Paper Analyser (Port 8001)

```bash
POST /tools/obp.paper.search
POST /tools/obp.paper.analyze
POST /tools/obp.claims.extract
GET /health
```

### DatasetSmith Backend (Port 8000)

```bash
POST /api/chats
POST /api/chat
GET /api/download-progress
POST /api/start-full-run
GET /download/{id}
DELETE /api/datasets/{id}
GET /health
```

---

## License

MIT License - see LICENSE file for details

---

## Contact

- GitHub: [@exploring-curiosity](https://github.com/exploring-curiosity)
- Project: [OpenBenchPublisher](https://github.com/exploring-curiosity/OpenBenchPublisher)

---

**DatasetSmith Platform** - Making ML research reproducible, accessible, and lightning-fast.
