# OpenBench Publisher (OBP)

**An AI-powered research assistant that helps ML researchers discover papers, analyze claims, and generate reproducible datasets.**

Powered by **Tavily** for intelligent paper discovery, **MongoDB Atlas** for vector search, and **OpenAI** for intelligent analysis.

---

## ✨ What It Does

**Problem:** ML research moves fast—papers appear daily, claims are hard to verify, and reproducing results requires matching the exact dataset specifications.

**Solution:** OpenBench Publisher automates the research workflow:

1. **🔍 Discover Papers** - Search recent ML papers using Tavily's advanced search with domain filtering and recency controls
2. **📊 Analyze Claims** - Extract key information: tasks, datasets, metrics, and reported results using LLM-powered analysis
3. **🎯 Generate Dataset Queries** - Automatically create structured dataset specifications that enable reproduction of paper results

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MongoDB Atlas account (free tier works)
- API keys: Tavily, OpenAI

### Installation

```bash
# Clone the repository
git clone https://github.com/vaishnavi121999/OpenBenchPublisher.git
cd OpenBenchPublisher

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Create a `.env` file with:
```bash
TAVILY_API_KEY="your_tavily_key"
MONGODB_URI="your_mongodb_connection_string"
MONGODB_DB="obp"
OPENAI_API_KEY="your_openai_key"
OPENAI_MODEL="gpt-4o-mini"
```

### Run the Application

```bash
python -m obp.mcp_server
```

Open your browser to: **http://localhost:8000**

---

## 🎯 Key Features

### 1. Intelligent Paper Discovery
- Search papers by topic, domain, and time range
- Filter by source (arXiv, CVPR, etc.)
- Advanced Tavily search with customizable parameters

### 2. Automated Analysis
- Extract paper summaries using GPT-4o-mini
- Identify datasets and tasks mentioned
- Parse evaluation claims with metrics and results
- Store embeddings for semantic search

### 3. Dataset Query Generation ⭐
**Our unique feature:** Automatically generate structured dataset specifications from papers.

**Example Output:**
```
3-class urban transport images
"Build a 3-class image dataset with about 10 images total of bicycles, 
electric scooters, and city buses in real urban environments (streets, 
bike lanes, bus stops). Aim for roughly 3 images per class, diverse 
cities and angles, no stock-photo watermarks."
```

This enables researchers to:
- Reproduce paper experiments with matching datasets
- Understand exact data requirements
- Generate datasets using automated tools

---

## 💡 How to Use

### Search for Papers
1. Enter a research topic (e.g., "depth estimation", "transformer models")
2. Select time range and domains
3. Click "Search" to discover relevant papers

### Analyze a Paper
1. Paste a paper URL (arXiv, conference proceedings, etc.)
2. Click "Analyze paper"
3. View:
   - **Summary** - Concise overview of the paper
   - **Dataset Query** - Structured specification for reproduction
   - **Detected Datasets** - Datasets mentioned in the paper
   - **Claims** - Extracted evaluation results

### Copy Dataset Query
Click the "Copy Query" button to copy the dataset specification and use it with dataset generation tools.

---

## 🏗️ Architecture

```
Web UI (FastAPI + Vanilla JS)
    ↓
Paper Analysis Pipeline
    ├─ Tavily API (paper discovery & content extraction)
    ├─ OpenAI GPT-4o-mini (summarization & claim extraction)
    └─ MongoDB Atlas (storage with vector search)
```

### Tech Stack
- **Backend:** FastAPI, Python 3.11
- **Frontend:** Vanilla JavaScript, Modern CSS
- **APIs:** Tavily, OpenAI
- **Database:** MongoDB Atlas with Vector Search
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)

---

## 📊 API Endpoints

### `POST /tools/obp.paper.search`
Search for papers using Tavily

**Request:**
```json
{
  "query": "depth estimation",
  "time_range": "week",
  "include_domains": ["arxiv.org"],
  "max_results": 10
}
```

### `POST /tools/obp.paper.analyze`
Analyze a paper and generate dataset query

**Request:**
```json
{
  "paper_url": "https://arxiv.org/abs/2312.17238"
}
```

**Response:**
```json
{
  "paper_id": "...",
  "title": "Paper Title",
  "summary": "3-6 sentence summary",
  "dataset_query": "Title\n\"Detailed instruction...\"",
  "datasets": ["COCO", "ImageNet"],
  "tasks": ["object detection"],
  "claims": [...]
}
```

---

## 🎓 Use Cases

- **Researchers:** Quickly understand new papers and reproduce results
- **Students:** Learn about experimental setups and dataset requirements
- **Engineers:** Generate dataset specifications for ML projects
- **Reviewers:** Verify claims and understand data requirements

---

## 🤝 Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

Built with:
- [Tavily](https://tavily.com) - AI-powered search API
- [MongoDB Atlas](https://www.mongodb.com/atlas) - Cloud database with vector search
- [OpenAI](https://openai.com) - GPT-4o-mini for analysis
- [FastAPI](https://fastapi.tiangolo.com) - Modern web framework

---

**OpenBench Publisher** - Making ML research reproducible, one paper at a time.
