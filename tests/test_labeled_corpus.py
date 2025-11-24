import csv
import logging
from uuid import uuid4

from obp.agents.foundational_gatherer import FoundationalGatherer
from obp.downloader import FoundationalDownloader
from obp.export import exporter


logging.basicConfig(level=logging.INFO)


def run_labeled_corpus_tests() -> None:
    gatherer = FoundationalGatherer()
    downloader = FoundationalDownloader()

    # Build a small multi-class TEXT corpus
    text_specs = [
        {"label": "people", "query": "short biographies of famous scientists"},
        {"label": "sports", "query": "match reports of recent football games"},
        {"label": "finance", "query": "news about stock market volatility"},
    ]

    text_request_specs = []
    for spec in text_specs:
        request_id = str(uuid4())
        label = spec["label"]
        query = spec["query"]

        print(f"\n=== TEXT CLASS '{label}' ===")
        print(f"Query: {query}")
        count = gatherer.gather_and_store(query, "text", request_id, limit=3)
        print(f"Gathered: {count}")
        if count == 0:
            continue

        sampled = gatherer.sample_resources(request_id, count_per_modality=2)
        print(f"Sampled: {sampled}")

        downloaded = downloader.download_all(request_id)
        print(f"Downloaded: {downloaded}")

        text_request_specs.append({"label": label, "request_id": request_id})

    if text_request_specs:
        path = exporter.build_labeled_corpus(text_request_specs, modality="text")
        print("\nLabeled TEXT corpus:", path)
        if path:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            print(f"Rows: {len(rows)} | Columns: {reader.fieldnames}")

    # Build a small multi-class NUMERICAL corpus
    numerical_specs = [
        {"label": "emissions", "query": "Global CO2 emissions by country 2023 csv"},
        {"label": "gdp", "query": "World Bank GDP per capita by country csv"},
    ]

    numerical_request_specs = []
    for spec in numerical_specs:
        request_id = str(uuid4())
        label = spec["label"]
        query = spec["query"]

        print(f"\n=== NUMERICAL CLASS '{label}' ===")
        print(f"Query: {query}")
        count = gatherer.gather_and_store(query, "numerical", request_id, limit=3)
        print(f"Gathered: {count}")
        if count == 0:
            continue

        sampled = gatherer.sample_resources(request_id, count_per_modality=2)
        print(f"Sampled: {sampled}")

        downloaded = downloader.download_all(request_id)
        print(f"Downloaded: {downloaded}")

        numerical_request_specs.append({"label": label, "request_id": request_id})

    if numerical_request_specs:
        path = exporter.build_labeled_corpus(numerical_request_specs, modality="numerical")
        print("\nLabeled NUMERICAL corpus:", path)
        if path:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            print(f"Rows: {len(rows)} | Columns: {reader.fieldnames}")


if __name__ == "__main__":
    run_labeled_corpus_tests()
