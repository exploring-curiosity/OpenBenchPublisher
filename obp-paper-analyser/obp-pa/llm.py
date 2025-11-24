import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import settings


_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.has_openai:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env to enable LLM-based analysis."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _resolve_model_name(model: Optional[str]) -> str:
    if model:
        return model
    if getattr(settings, "openai_model", None):
        return settings.openai_model
    return "gpt-4o-mini"


def analyze_paper_with_llm(
    full_text: str,
    title: Optional[str],
    url: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Use a small OpenAI model to summarize a paper and detect datasets/tasks.

    Returns a dict with keys: summary (str), datasets (list[str]), tasks (list[str]).
    If parsing fails, returns a minimal fallback.
    """
    client = get_openai_client()

    # Truncate very long texts to keep prompts manageable.
    max_chars = 12000
    text_snippet = full_text[:max_chars]

    system_msg = (
        "You are a research assistant that reads ML papers and outputs STRICT JSON. "
        "Given the title, URL, and full text (possibly noisy HTML), you must return a JSON object "
        "with fields: summary (string, 3-6 sentences), datasets (array of strings), tasks (array of strings). "
        "Datasets and tasks should be concise canonical names (e.g. 'CIFAR-10', 'ImageNet', 'code generation'). "
        "If unsure, use empty arrays for datasets and tasks. DO NOT include any other keys or commentary."
    )

    user_msg = (
        f"Title: {title or ''}\n"
        f"URL: {url}\n\n"
        "Full text (may include HTML or boilerplate):\n" + text_snippet
    )

    model_name = _resolve_model_name(model)

    chat = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )

    content = chat.choices[0].message.content or "{}"

    try:
        data = json.loads(content)
    except Exception:
        # Fallback minimal structure
        return {"summary": "", "datasets": [], "tasks": []}

    summary = data.get("summary") or ""
    datasets = data.get("datasets") or []
    tasks = data.get("tasks") or []

    # Basic type normalization
    if not isinstance(datasets, list):
        datasets = []
    if not isinstance(tasks, list):
        tasks = []

    datasets = [str(d).strip() for d in datasets if str(d).strip()]
    tasks = [str(t).strip() for t in tasks if str(t).strip()]

    return {"summary": str(summary), "datasets": datasets, "tasks": tasks}


def extract_claims_with_llm(
    full_text: str,
    title: Optional[str],
    url: str,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Use an OpenAI model to extract structured evaluation claims from a paper.

    Returns a list of dicts with keys: task, dataset, metric, reported, setup.
    """
    client = get_openai_client()
    model_name = _resolve_model_name(model)

    max_chars = 10000
    text_snippet = full_text[:max_chars]

    system_msg = (
        "You are a research assistant extracting evaluation claims from ML papers. "
        "Output STRICT JSON with a single key 'claims' whose value is an array of objects. "
        "Each object MUST have keys: task (string or null), dataset (string or null), "
        "metric (string or null), reported (number or null), setup (string). "
        "Focus on concrete empirical results (e.g. accuracy on a dataset) rather than general discussion. "
        "If no clear claims exist, return {\"claims\": []}. DO NOT output any other text."
    )

    user_msg = (
        f"Title: {title or ''}\n"
        f"URL: {url}\n\n"
        "Full text (may include HTML or boilerplate):\n" + text_snippet
    )

    chat = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )

    content = chat.choices[0].message.content or "{}"

    try:
        data = json.loads(content)
    except Exception:
        return []

    claims = data.get("claims") or []
    if not isinstance(claims, list):
        return []

    cleaned: List[Dict[str, Any]] = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        task = c.get("task")
        dataset = c.get("dataset")
        metric = c.get("metric")
        reported = c.get("reported")
        setup = c.get("setup")

        cleaned.append(
            {
                "task": str(task).strip() if task is not None else None,
                "dataset": str(dataset).strip() if dataset is not None else None,
                "metric": str(metric).strip() if metric is not None else None,
                "reported": float(reported) if isinstance(reported, (int, float)) else None,
                "setup": str(setup).strip() if setup is not None else "",
            }
        )

    return [c for c in cleaned if c["setup"]]


def generate_dataset_query_for_paper(
    *,
    summary: str,
    datasets: List[str],
    tasks: List[str],
    claims: List[Dict[str, Any]],
    title: Optional[str],
    url: str,
    model: Optional[str] = None,
) -> str:
    """Generate a single dataset-generation prompt string for a paper.

    This is intended to be copied into a collaborator's dataset generator, in the
    style of: "Build a 3-class image dataset with about 10 images total of bicycles, 
    electric scooters, and city buses in real urban environments...".
    """
    client = get_openai_client()
    model_name = _resolve_model_name(model)

    # Keep prompt compact but informative.
    claims_snippet: List[Dict[str, Any]] = claims[:5]

    system_msg = (
        "You help ML researchers design small evaluation datasets to reproduce paper results. "
        "Given a paper's title, URL, summary, detected tasks/datasets, and evaluation claims, "
        "write ONE concise dataset-generation instruction that enables reproducing the paper's experiments. "
        "\n\n"
        "CRITICAL FORMAT REQUIREMENTS:\n"
        "1. Start with a brief title describing the dataset (e.g., '3-class urban transport images')\n"
        "2. Follow with a detailed instruction in quotes that specifies:\n"
        "   - Number of classes and total images/samples\n"
        "   - Specific categories/classes to include\n"
        "   - Context or environment details\n"
        "   - Approximate distribution (e.g., 'roughly 3 images per class')\n"
        "   - Quality requirements (e.g., 'diverse cities and angles, no stock-photo watermarks')\n"
        "\n"
        "EXAMPLE FORMAT:\n"
        "3-class urban transport images\n"
        "\"Build a 3-class image dataset with about 10 images total of bicycles, electric scooters, "
        "and city buses in real urban environments (streets, bike lanes, bus stops). Aim for roughly "
        "3 images per class, diverse cities and angles, no stock-photo watermarks.\"\n"
        "\n"
        "Output ONLY the title and quoted instruction. Do NOT add explanations or commentary."
    )

    user_payload = {
        "title": title,
        "url": url,
        "summary": summary,
        "datasets": datasets,
        "tasks": tasks,
        "claims": claims_snippet,
    }

    user_msg = (
        "Here is the paper information as JSON. Generate a dataset-generation query "
        "in the exact format specified (title + quoted instruction).\n\n" 
        + json.dumps(user_payload, ensure_ascii=False)
    )

    chat = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.4,
    )

    content = chat.choices[0].message.content or ""
    # Return the raw content; caller can trim whitespace.
    return content.strip()
