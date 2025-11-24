import asyncio
import logging

from obp.agents.dataset_smith import dataset_smith
from obp.export import exporter


logging.basicConfig(level=logging.INFO)


async def run_tests() -> None:
    scenarios = [
        ("Single-class: cats", ["cat"], 20),
        (
            "Multi-class: people/cars/books/dogs/mountains",
            ["person", "car", "book", "dog", "mountain"],
            100,
        ),
    ]

    for name, classes, total in scenarios:
        print("\n" + "=" * 60)
        print(name)
        print(f"Classes: {classes} | total target: {total}")

        manifest = await dataset_smith.build_slice(
            classes=classes,
            total=total,
            min_size=256,
        )

        dataset_id = manifest["dataset_id"]
        print(f"Dataset ID: {dataset_id}")

        summary = exporter.export_dataset(dataset_id=dataset_id)
        print(f"Output dir: {summary['output_dir']}")
        print(f"Exported counts: {summary['exported_counts']}")
        print(f"Total exported: {summary['total_exported']}")


if __name__ == "__main__":
    asyncio.run(run_tests())
