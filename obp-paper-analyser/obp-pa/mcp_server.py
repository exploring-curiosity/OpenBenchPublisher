import os
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .paper_search import search_papers, DEFAULT_PAPER_DOMAINS
from .claims import extract_claims_for_paper_url
from .paper_analysis import analyze_paper_url


class PaperSearchRequest(BaseModel):
    query: str = Field(...)
    search_depth: str = Field("advanced")
    time_range: Optional[str] = Field("day")
    start_date: Optional[str] = Field(None)
    end_date: Optional[str] = Field(None)
    include_domains: Optional[List[str]] = Field(None)
    exclude_domains: Optional[List[str]] = Field(default_factory=list)
    max_results: int = Field(10, ge=1, le=20)
    include_raw_content: bool = Field(True)
    auto_parameters: bool = Field(False)
    topic: str = Field("general")


class PaperResult(BaseModel):
    id: int
    title: Optional[str]
    url: Optional[str]
    domain: Optional[str]
    content: Optional[str]
    raw_content: Optional[str]
    score: Optional[float]
    published_date: Optional[str]


class PaperSearchResponse(BaseModel):
    query: str
    papers: List[PaperResult]
    tavily_meta: Dict[str, Any]


class ClaimsExtractRequest(BaseModel):
    paper_url: str = Field(..., description="URL of the paper to extract claims from")


class Claim(BaseModel):
    id: str
    paper_id: str
    task: Optional[str]
    dataset: Optional[str]
    metric: Optional[str]
    reported: Optional[float]
    setup: str


class ClaimsExtractResponse(BaseModel):
    paper_id: str
    claims: List[Claim]


class PaperAnalyzeRequest(BaseModel):
    paper_url: str = Field(..., description="URL of the paper to analyze")


class PaperAnalyzeResponse(BaseModel):
    paper_id: str
    title: Optional[str]
    links: List[str]
    summary: str
    datasets: List[str]
    tasks: List[str]
    dataset_query: Optional[str] = None
    claims: List[Claim]


app = FastAPI(title="OpenBench Publisher MCP Stub", version="0.1.0")


BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "web")

if os.path.isdir(STATIC_DIR):
    app.mount("/web", StaticFiles(directory=STATIC_DIR, html=True), name="web")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    # Redirect to the mounted static web UI so that relative asset paths
    # resolve correctly (styles.css, app.js under /web/).
    return RedirectResponse(url="/web/", status_code=307)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/tools/obp.paper.search", response_model=PaperSearchResponse)
def obp_paper_search(payload: PaperSearchRequest) -> PaperSearchResponse:
    try:
        result = search_papers(
            query=payload.query,
            search_depth=payload.search_depth,
            time_range=payload.time_range,
            start_date=payload.start_date,
            end_date=payload.end_date,
            include_domains=payload.include_domains or DEFAULT_PAPER_DOMAINS,
            exclude_domains=payload.exclude_domains,
            max_results=payload.max_results,
            include_raw_content=payload.include_raw_content,
            auto_parameters=payload.auto_parameters,
            topic=payload.topic,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result  # type: ignore[return-value]


@app.post("/tools/obp.paper.analyze", response_model=PaperAnalyzeResponse)
def obp_paper_analyze(payload: PaperAnalyzeRequest) -> PaperAnalyzeResponse:
    try:
        result = analyze_paper_url(payload.paper_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result  # type: ignore[return-value]


@app.post("/tools/obp.claims.extract", response_model=ClaimsExtractResponse)
def obp_claims_extract(payload: ClaimsExtractRequest) -> ClaimsExtractResponse:
    try:
        result = extract_claims_for_paper_url(payload.paper_url)
    except ValueError as e:
        # e.g., Tavily could not find or parse the paper content
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # e.g., MongoDB config issues
        raise HTTPException(status_code=500, detail=str(e))

    return result  # type: ignore[return-value]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("obp-pa.mcp_server:app", host="0.0.0.0", port=8001, reload=True)
