import re
from typing import Any, Dict, List, Optional

from .tavily_client import get_tavily_client
from .db import get_papers_collection, get_claims_collection
from .embeddings import embed_texts


METRIC_KEYWORDS = [
    "accuracy",
    "acc",
    "top-1",
    "top-5",
    "f1",
    "f1-score",
    "precision",
    "recall",
    "map",
    "mean average precision",
    "iou",
    "intersection over union",
    "bleu",
    "rouge",
]

DATASET_KEYWORDS = [
    "cifar-10",
    "cifar10",
    "cifar-100",
    "imagenet",
    "imagenet-1k",
    "mscoco",
    "coco",
    "mnist",
    "svhn",
    "cityscapes",
    "pascal voc",
]

TASK_KEYWORDS = [
    "classification",
    "image classification",
    "object detection",
    "segmentation",
    "semantic segmentation",
    "instance segmentation",
    "depth estimation",
    "pose estimation",
]


def _find_first_keyword(keywords: List[str], text: str) -> Optional[str]:
    lower = text.lower()
    for kw in keywords:
        if kw in lower:
            return kw
    return None


def _extract_numeric_value(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%?", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _split_sentences(text: str) -> List[str]:
    # Very simple sentence splitter; good enough for hackathon heuristics.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def extract_claims_for_paper_url(paper_url: str) -> Dict[str, Any]:
    """Fetch a paper via Tavily, store it in MongoDB, and extract heuristic claims.

    Returns a dict of the form:
      { "paper_id": str, "claims": [{id, paper_id, task, dataset, metric, reported, setup}] }
    """
    tavily_client = get_tavily_client()

    # Use Tavily search to retrieve the main page for this paper URL.
    response = tavily_client.search(
        query=paper_url,
        max_results=1,
        search_depth="advanced",
        include_raw_content=True,
        include_answer=False,
    )

    results = response.get("results", [])
    if not results:
        raise ValueError(f"No Tavily results found for paper_url={paper_url!r}")

    result = results[0]
    title = result.get("title")
    url = result.get("url") or paper_url

    content_parts: List[str] = []
    if result.get("content"):
        content_parts.append(result["content"])
    if result.get("raw_content"):
        content_parts.append(result["raw_content"])

    full_text = "\n\n".join(content_parts).strip()
    if not full_text:
        raise ValueError("Tavily did not return usable content for this paper.")

    # Embed the full paper text.
    paper_embedding = embed_texts([full_text])[0]

    papers_col = get_papers_collection()
    paper_doc: Dict[str, Any] = {
        "title": title,
        "links": [url],
        "abstract": None,
        "content": full_text,
        "embed": paper_embedding,
    }
    paper_insert = papers_col.insert_one(paper_doc)
    paper_id = paper_insert.inserted_id

    # Very simple heuristic claim extraction: look for metric-like sentences.
    sentences = _split_sentences(full_text)
    candidate_sentences: List[str] = []

    for s in sentences:
        lower = s.lower()
        if any(kw in lower for kw in METRIC_KEYWORDS):
            candidate_sentences.append(s)

    if not candidate_sentences:
        # Fall back to the first few sentences if we couldn't find any metric lines.
        candidate_sentences = sentences[:5]

    if not candidate_sentences:
        return {"paper_id": str(paper_id), "claims": []}

    claim_embeddings = embed_texts(candidate_sentences)

    claims_col = get_claims_collection()
    claim_docs: List[Dict[str, Any]] = []

    for sentence, emb in zip(candidate_sentences, claim_embeddings):
        metric = _find_first_keyword(METRIC_KEYWORDS, sentence)
        dataset = _find_first_keyword(DATASET_KEYWORDS, sentence)
        task = _find_first_keyword(TASK_KEYWORDS, sentence)
        reported = _extract_numeric_value(sentence)

        claim_docs.append(
            {
                "paper_id": paper_id,
                "task": task,
                "dataset": dataset,
                "metric": metric,
                "reported": reported,
                "setup": sentence,
                "embed": emb,
            }
        )

    if not claim_docs:
        return {"paper_id": str(paper_id), "claims": []}

    insert_result = claims_col.insert_many(claim_docs)
    inserted_ids = insert_result.inserted_ids

    api_claims: List[Dict[str, Any]] = []
    for oid, doc in zip(inserted_ids, claim_docs):
        api_claims.append(
            {
                "id": str(oid),
                "paper_id": str(paper_id),
                "task": doc["task"],
                "dataset": doc["dataset"],
                "metric": doc["metric"],
                "reported": doc["reported"],
                "setup": doc["setup"],
            }
        )

    return {"paper_id": str(paper_id), "claims": api_claims}
