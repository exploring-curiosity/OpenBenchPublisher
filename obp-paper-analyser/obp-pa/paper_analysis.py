import re
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

from .tavily_client import get_tavily_client
from .db import get_papers_collection, get_claims_collection
from .embeddings import embed_texts
from .claims import METRIC_KEYWORDS, DATASET_KEYWORDS, TASK_KEYWORDS
from .llm import (
    analyze_paper_with_llm,
    extract_claims_with_llm,
    generate_dataset_query_for_paper,
)


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _find_first_keyword(keywords: List[str], text: str) -> Optional[str]:
    lower = text.lower()
    for kw in keywords:
        if kw in lower:
            return kw
    return None


def _find_all_keywords(keywords: List[str], text: str) -> List[str]:
    lower = text.lower()
    found = []
    for kw in keywords:
        if kw in lower:
            found.append(kw)
    # keep order but unique
    seen = set()
    unique = []
    for kw in found:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


def _extract_numeric_value(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%?", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _build_summary(full_text: str) -> str:
    lower = full_text.lower()
    idx = lower.find("abstract")
    window = full_text
    if idx != -1:
        window = full_text[idx : idx + 2000]
    sentences = _split_sentences(window)
    if not sentences:
        sentences = _split_sentences(full_text)
    summary = " ".join(sentences[:5])
    return summary[:1500]


def _collect_crawl_text(tavily_client: TavilyClient, url: str) -> str:
    try:
        response = tavily_client.crawl(url, instructions="Retrieve the main content of this research paper, including abstract and methodology.")
    except Exception:
        return ""

    parts: List[str] = []
    for r in response.get("results", []):
        raw = r.get("raw_content")
        if raw:
            parts.append(raw)
    return "\n\n".join(parts).strip()


def analyze_paper_url(paper_url: str) -> Dict[str, Any]:
    tavily_client = get_tavily_client()

    search_response = tavily_client.search(
        query=paper_url,
        max_results=1,
        search_depth="advanced",
        include_raw_content=True,
        include_answer=False,
    )

    results = search_response.get("results", [])
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

    search_text = "\n\n".join(content_parts).strip()

    crawl_text = _collect_crawl_text(tavily_client, url)

    full_text_candidates = [t for t in [crawl_text, search_text] if t]
    if not full_text_candidates:
        raise ValueError("Tavily did not return usable content for this paper.")

    full_text = "\n\n".join(full_text_candidates)

    paper_embedding = embed_texts([full_text])[0]

    # Heuristic initial guesses
    datasets = _find_all_keywords(DATASET_KEYWORDS, full_text)
    tasks = _find_all_keywords(TASK_KEYWORDS, full_text)
    summary = _build_summary(full_text)

    # Refine summary/datasets/tasks with a small OpenAI model if available.
    try:
        llm_result = analyze_paper_with_llm(full_text, title, url)
        llm_summary = llm_result.get("summary") or ""
        llm_datasets = llm_result.get("datasets") or []
        llm_tasks = llm_result.get("tasks") or []

        if llm_summary:
            summary = llm_summary
        if llm_datasets:
            datasets = llm_datasets
        if llm_tasks:
            tasks = llm_tasks
    except Exception:
        # If the LLM call fails for any reason, silently fall back to heuristics.
        pass

    papers_col = get_papers_collection()
    paper_doc: Dict[str, Any] = {
        "title": title,
        "links": [url],
        "abstract": None,
        "content": full_text,
        "summary": summary,
        "datasets": datasets,
        "tasks": tasks,
        # dataset_query will be added after we construct it below.
        "embed": paper_embedding,
    }
    paper_insert = papers_col.insert_one(paper_doc)
    paper_id = paper_insert.inserted_id

    sentences = _split_sentences(full_text)
    api_claims: List[Dict[str, Any]] = []

    # Prefer LLM-based structured claim extraction when available.
    try:
        structured_claims = extract_claims_with_llm(full_text, title, url)
    except Exception:
        structured_claims = []

    if structured_claims:
        sentences_for_embed = [c.get("setup") or "" for c in structured_claims if c.get("setup")]
        claim_embeddings = embed_texts(sentences_for_embed) if sentences_for_embed else []
        claims_col = get_claims_collection()
        claim_docs: List[Dict[str, Any]] = []

        for c, emb in zip(structured_claims, claim_embeddings):
            claim_docs.append(
                {
                    "paper_id": paper_id,
                    "task": c.get("task"),
                    "dataset": c.get("dataset"),
                    "metric": c.get("metric"),
                    "reported": c.get("reported"),
                    "setup": c.get("setup"),
                    "embed": emb,
                }
            )

        if claim_docs:
            insert_result = claims_col.insert_many(claim_docs)
            inserted_ids = insert_result.inserted_ids
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
    else:
        # Fallback: heuristic keyword-based candidate sentences.
        candidate_sentences: List[str] = []
        for s in sentences:
            lower = s.lower()
            if any(kw in lower for kw in METRIC_KEYWORDS):
                candidate_sentences.append(s)

        if not candidate_sentences:
            candidate_sentences = sentences[:5]

        if candidate_sentences:
            claim_embeddings = embed_texts(candidate_sentences)
            claims_col = get_claims_collection()
            claim_docs = []

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

            if claim_docs:
                insert_result = claims_col.insert_many(claim_docs)
                inserted_ids = insert_result.inserted_ids
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

    # Now that we have summary/datasets/tasks/claims, generate a dataset_query
    # suggestion for downstream dataset builders.
    dataset_query = ""
    try:
        dataset_query = generate_dataset_query_for_paper(
            summary=summary,
            datasets=datasets,
            tasks=tasks,
            claims=api_claims,
            title=title,
            url=url,
        )
    except Exception:
        dataset_query = ""

    # Update the stored paper document with the dataset_query field.
    if dataset_query:
        papers_col.update_one(
            {"_id": paper_id},
            {"$set": {"dataset_query": dataset_query}},
        )

    return {
        "paper_id": str(paper_id),
        "title": title,
        "links": [url],
        "summary": summary,
        "datasets": datasets,
        "tasks": tasks,
        "dataset_query": dataset_query,
        "claims": api_claims,
    }
