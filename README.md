# OpenBench Publisher (OBP)

**An MCP-native research agent that discovers papers via Tavily, builds license-clean dataset slices, runs micro-repro evaluations, and publishes citable _Data Cards_ & _Repro Cards_.**

State lives in **MongoDB Atlas** with **Vector Search**. Exposed as an **MCP server** and orchestrated by **LastMile's mcp-agent**.

---

## ✨ What It Does

**Problem:** ML research is noisy—new papers appear daily, claims are hard to reproduce, datasets are buried in PDFs, and there's no standard way to track "what was claimed, on what data, and what independent re-evaluations show."

**Solution:** OBP is a research-ops agent that:

1. **Discovers** new papers via **Tavily** (with advanced search, recency filters, domain filtering).
2. **Extracts** claims (task, dataset, metric, reported results) and stores them in **MongoDB Atlas** with embeddings.
3. **Builds** license-clean dataset slices (via Tavily image/data search + MongoDB Vector Search for dedupe).
4. **Runs** CPU-only micro-repro evaluations on small slices.
5. **Publishes** citable **Data Cards** (for slices) and **Repro Cards** (for runs) with provenance, license info, and observed vs reported metrics.

**Key Tech:**
- **Tavily**: all discovery (papers, datasets, images) with `search_depth=advanced`, `include_raw_content`, `include_images`, domain allow/deny lists.
- **MongoDB Atlas Vector Search**: stores papers/claims/assets with embeddings; used for semantic search and near-duplicate detection.
- **LastMile MCP**: OBP is an **MCP server** exposing `obp.*` tools, orchestrated by **mcp-agent** sub-agents (PaperScout, DatasetSmith, ReproRunner, Publisher).
- **CPU-only**: lightweight models (sentence-transformers, OpenCLIP, Tesseract OCR, pHash/SSIM) for embeddings, dedupe, and evals.

---

## 🏆 Prize Track Alignment
- **Overall:** real-world agent that automates discover → slice → repro → publish.
- **Tavily (Primary):** OBP showcases Tavily parameters in traces: `topic`, `search_depth`, `time_range`/`start_date/end_date`, `auto_parameters`, `include_raw_content`, `include_images(+descriptions)`, `include_domains`/`exclude_domains`, `chunks_per_source`, `country`, `max_results`.
- **MongoDB Atlas:** Vector Search on `papers.embed`, `claims.embed`, `assets.img_embed`; change streams to live-update UI.
- **LastMile AI:** End-to-end on **mcp-agent**, exposed as **MCP server** via **mcp-c**, usable daily from a **ChatGPT App** (plus a “watcher” that posts new Cards automatically).

---

## 🧱 Architecture (Tavily-first)

```
Clients
├─ ChatGPT App (MCP client) — natural chat & buttons (Replicate / Build Slice / Publish)
└─ Web UI (Next.js) — read-only dashboards: Feed, Data Cards, Repro Cards, Provenance Graph

OBP MCP Server (mcp-c)
└─ Tools (high-level):
   • obp.paper.search(query, tavily_params)
   • obp.claims.extract(paper_url|paper_id)
   • obp.slice.build(spec)
   • obp.repro.run(claim_id, slice_id|spec, budget)
   • obp.card.publish(type, payload), obp.card.get(id)
   • obp.search.similar(kind,id,k,filters)
   • obp.admin.watch(feed_spec)  ← daily paper watcher

Agent Orchestrators (LastMile mcp-agent)
├─ PaperScout   — Tavily discovery, PDF parse, claim extraction
├─ DatasetSmith — spec→slice: license filter, dedupe, manifest, Data Card
├─ ReproRunner  — micro-eval on slice, metrics compare, Repro Card
└─ Publisher    — card signing & publishing, watchers

Tool Servers & Services
├─ Tavily MCP/API — discovery (papers, repos, datasets, posts, errata)
├─ Media/OCR/Embeddings — fetch, screenshot, Tesseract OCR, CLIP/OpenCLIP, pHash/SSIM
├─ Eval Pods (sandboxed) — CPU-capped micro-evals (no training)
└─ Dagster (optional) — schedules scouts, materializes slices, triggers publishes

Data & Artifacts
└─ MongoDB Atlas + Object Storage
   • papers, claims, assets, datasets, runs, cards (with Vector Search)
   • PDFs/screenshots/manifests/logs in object store, referenced from DB
```

---

## 🧭 Core Flows (Implementable for Hackathon)

### Flow 1: Paper Discovery → Repro Card

**User prompt:** _"Replicate yesterday's cs.CV paper on depth estimation using a small CIFAR-10 slice."_

1. **`obp.paper.search`** → Tavily search with:
   - `query="cs.CV depth estimation"`, `time_range="day"`, `search_depth="advanced"`
   - `include_domains=["arxiv.org","openaccess.thecvf.com"]`
   - Returns: list of papers with titles, URLs, abstracts, raw content.

2. **`obp.claims.extract`** → Parse paper (PDF/HTML) to extract:
   - Task, dataset, metric, reported value, setup/env.
   - Generate embeddings (sentence-transformers) and store in `papers`, `claims` collections.

3. **`obp.slice.build`** → Build a small eval slice:
   - Use existing CIFAR-10 subset or Tavily image search for custom classes.
   - Dedupe via pHash + MongoDB `$vectorSearch` on `assets.img_embed`.
   - Store manifest + metadata.

4. **`obp.repro.run`** → Run micro-eval:
   - Load pretrained model (e.g., ResNet18), run on slice, record observed metrics.
   - Compare observed vs reported.

5. **`obp.card.publish`** → Publish Repro Card:
   - Reported vs observed bars, Δ%, env hash, logs reference, slice provenance.

---

### Flow 2: Dataset Slice Builder → Data Card

**User prompt:** _"Build a 500-image cats vs dogs slice, CC-BY only, min 512px, balanced 50/50."_

1. **`obp.slice.build`** with spec:
   - `classes=["cat","dog"]`, `total=500`, `split=[0.7,0.15,0.15]`, `license="CC-BY"`, `min_size=512`.

2. **Tavily image search** per class:
   - `search_depth="advanced"`, `include_images=true`, `include_image_descriptions=true`
   - `include_domains=["wikimedia.org","unsplash.com","pexels.com"]`

3. **Fetch + screen**:
   - Download images, check resolution, run license heuristics.
   - OCR/caption → text blob → VoyageAI embeddings.

4. **Dedupe**:
   - pHash for exact/near-exact duplicates.
   - MongoDB `$vectorSearch` on `assets.img_embed` for semantic near-dups.

5. **Balance + split**:
   - Enforce 50/50 class balance, stratified train/val/test split.

6. **`obp.card.publish`** → Data Card:
   - License table, class balance chart, dedupe stats, sample grid, provenance graph.

---

## 🗂️ Data Model (MongoDB Atlas)

**Collections & key fields**
- `papers{ _id, title, links, abstract, embed[] }`  **(vector index)**
- `claims{ _id, paper_id, task, dataset, metric, reported, setup, embed[] }`  **(vector index)**
- `assets{ _id, uri, license, width, phash, text_blob, img_embed[] }`  **(vector index)**
- `datasets{ _id, spec(json), manifest_sha, slice_stats, provenance }`
- `runs{ _id, claim_id, slice_id, env_hash, logs_ref, metrics }`
- `cards{ _id, type:"Data"|"Repro", payload(json), signed_at, version }`

**Vector Search**
- Index `papers.embed`, `claims.embed`, `assets.img_embed` (cosine).  
- Use `$vectorSearch` as **first** agg stage; add pre-filters (e.g., `{task, year, license, class}`).

---

## 🧩 OBP MCP Tool Surface (for LastMile prize)

| Tool | Input | Output |
|---|---|---|
| `obp.paper.search` | `query`, **Tavily params**: `topic`, `search_depth`, `auto_parameters`, `time_range` / `start_date/end_date`, `include_raw_content`, `include_images(+descriptions)`, `include_domains`, `exclude_domains`, `chunks_per_source`, `country`, `max_results` | `{ papers:[{id,title,url,abstract,...}] }` |
| `obp.claims.extract` | `paper_url` or `paper_id` | `{ claims:[{id,task,dataset,metric,reported,setup}] }` |
| `obp.slice.build` | `spec` (classes/counts/splits/licensing/min_px/strata + discovery options) | `{ slice_id, manifest_ref, stats, card_id }` |
| `obp.repro.run` | `claim_id`, `slice_id` or `spec`, `budget` | `{ run_id, observed:{metric,val}, delta, env_hash, logs_ref, card_id }` |
| `obp.card.publish` / `obp.card.get` | payload / id | permalinked card |
| `obp.search.similar` | `kind,id,k,filters` | `$vectorSearch` results (near-dups / similar papers/assets) |
| `obp.admin.watch` | `feed_spec` (arXiv cats, cadence) | starts/stops daily watcher that posts Cards |

---

## 🖥️ CPU-Only Config (no GPU required)

**Models & libs**
- **Text embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384-d)  
- **Image embeddings:** OpenCLIP ViT-B/32 on CPU (batch 32–64)  
- **OCR:** Tesseract  
- **Dedupe:** pHash + SSIM (filter threshold then vector kNN)  
- **Eval:** use **pretrained** light checkpoints; **no training**  
  - Vision: `resnet18` / `mobilenetv3` on CIFAR-10-mini / COCO-mini  
  - NLP: `distilbert-base` (QA/cls), `t5-small` (tiny summarization)  
- **Slice sizes:** 500–1,000 assets (great visuals; quick runs)

**Why it works**  
OBP’s value is **agentic retrieval, explainable Cards, and vector search**—not heavy compute.

---

## ⚙️ Setup & Implementation Plan

### Phase 1: Environment & Dependencies

**1. API Keys (required):**
```bash
export TAVILY_API_KEY="..."           # Get from tavily.com
export MONGODB_URI="mongodb+srv://..."  # Atlas connection string
export MONGODB_DB="obp"
```

**2. Install dependencies:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**3. System dependencies:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
# apt-get install tesseract-ocr
```

**4. MongoDB Atlas setup:**
- Create a free M0 cluster at mongodb.com/atlas
- Create database `obp` with collections: `papers`, `claims`, `assets`, `datasets`, `runs`, `cards`
- Create vector search indexes (see Data Model section for schema)

---

### Phase 2: Implementation Roadmap (Hackathon-Friendly)

**Day 1: Core Infrastructure**
- [ ] `obp/` package structure + config.py (env vars)
- [ ] `obp/db.py` → MongoDB client + collection helpers
- [ ] `obp/mcp_server.py` → FastAPI stub exposing basic MCP tools
- [ ] `obp/tavily_client.py` → Tavily API wrapper with all search params
- [ ] `obp/embeddings.py` → VoyageAI + sentence-transformers wrapper
- [ ] Test: Tavily search → store in MongoDB → retrieve via vector search

**Day 2: Agent Flows**
- [ ] `obp/agents/paper_scout.py` → `obp.paper.search` + `obp.claims.extract`
- [ ] `obp/agents/dataset_smith.py` → `obp.slice.build` (Tavily images → dedupe → manifest)
- [ ] `obp/agents/repro_runner.py` → `obp.repro.run` (load model → eval → metrics)
- [ ] `obp/cards.py` → `obp.card.publish` (Data Card + Repro Card generation)
- [ ] Wire mcp-agent orchestrator to call tools in sequence
- [ ] Test: end-to-end flow from prompt → Card

**Day 3: Polish & Demo**
- [ ] Evidence UI (Streamlit): show Cards, provenance graph, vector search
- [ ] ChatGPT App integration (MCP client config)
- [ ] Demo script: "Replicate yesterday's paper" + "Build cats/dogs slice"
- [ ] Documentation: setup guide, API reference, demo video

---

## 🚀 Running the System

**1. Start MCP Server:**
```bash
python -m obp.mcp_server
# Exposes obp.* tools on localhost:8000 (or configured port)
```

**2. Start Agent Hub (orchestrator):**
```bash
python -m obp.agent_hub
# Starts PaperScout, DatasetSmith, ReproRunner, Publisher agents
```

**3. Connect from ChatGPT App (or any MCP client):**
- Add OBP MCP server URL in your MCP client config
- Try example prompts:
  - _"Find yesterday's cs.CV papers on depth estimation and replicate the top one."_
  - _"Build a 500-image cats vs dogs slice, CC-BY only, min 512px."_
  - _"Show me similar papers to claim #123."_

**4. Evidence UI (optional):**
```bash
streamlit run obp/ui/evidence.py
# Shows: Cards feed, provenance graph, vector search explorer
```

---

## 🧪 Demo Script (60–90s)
1) In the ChatGPT App:  
   **“Replicate yesterday’s cs.CV paper on CIFAR-10-mini.”**  
   → Trace shows **Tavily** params (advanced depth, recency, domains). Claims appear.
2) **Spec-to-Slice** builder → **Data Card** pops (license table, balance chart, dedupe before/after, sample grid).  
3) **Run micro-repro** → **Repro Card** pops (reported vs observed bars, Δ%, env hash, logs snippet).  
4) **Provenance Graph**: claim → slice → run → cards.  
5) **`search.similar`** on a sample to show Atlas **Vector Search** near-dups.

---

## 📊 Success Metrics
- **Discovery precision** (Tavily → relevant rate)  
- **Slice quality** (dedupe %, license breakdown, class balance error)  
- **Repro parity** (mean |Δ| between reported vs observed)  
- **Latency** (p50 card time)  
- **Autonomy** (# Cards/day from watcher)

---

## 🔒 Governance & Ethics
- Default **CC0/CC-BY** only; attribution in Data Cards  
- PII & unsafe content checks for scraped assets  
- Card signing (content hash + timestamp)  
- Sandboxed evals with strict CPU/RAM/time budgets

---

## 🧭 Roadmap
- Multi-task support beyond image/NLP (e.g., speech, small RAGs)  
- Forkable **Delta Cards** (compare runs/slices)  
- Author “assist” notes on Cards  
- Public Collections for courses/reading groups
