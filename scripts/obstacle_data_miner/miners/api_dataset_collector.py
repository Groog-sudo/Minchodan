"""API-only collection plan for weak obstacle classes.

This module deliberately avoids search-engine crawling. It uses dataset APIs
that provide structured annotations, then falls back to Kaggle discovery for
classes that are not reliably exposed by COCO/Open Images class taxonomies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from miners.fiftyone_miner import SOURCE_CLASS_MAPS, FiftyOneMiner


WEAK_TARGET_CLASSES: tuple[str, ...] = (
    "scooter",
    "carrier",
    "chair",
    "table",
    "kiosk",
    "fire_hydrant",
    "bench",
)


KAGGLE_QUERY_PLAN: dict[str, tuple[str, ...]] = {
    "scooter": (
        "electric scooter object detection",
        "kick scooter detection dataset",
    ),
    "carrier": (
        "suitcase luggage object detection",
        "travel suitcase detection dataset",
    ),
    "kiosk": (
        "self service kiosk detection",
        "kiosk object detection dataset",
    ),
    "chair": ("chair object detection dataset",),
    "table": ("table object detection dataset",),
    "fire_hydrant": ("fire hydrant object detection",),
    "bench": ("bench object detection dataset",),
}


@dataclass(frozen=True)
class CollectionJob:
    dataset_name: str
    split: str
    target_class: str
    max_samples: int


class APIDatasetCollector:
    """Collect weak classes from annotation-providing APIs only."""

    def __init__(self, export_root: Path | None = None) -> None:
        self.fiftyone = FiftyOneMiner(export_root=export_root)

    def collect_weak_classes(
        self,
        max_per_class: int = 100,
        split: str = "validation",
        datasets: tuple[str, ...] = ("coco-2017", "open-images-v7"),
    ) -> list[Path]:
        """Download mapped weak-class samples from supported FiftyOne datasets.

        Classes that are not in a dataset taxonomy are skipped with a clear
        message instead of triggering broad or accidental downloads.
        """

        exported_dirs: list[Path] = []
        for job in self._build_fiftyone_jobs(max_per_class=max_per_class, split=split, datasets=datasets):
            print(
                f"[FIFTYONE] {job.dataset_name} split={job.split} "
                f"class={job.target_class} max={job.max_samples}"
            )
            exported_dirs.append(
                self.fiftyone.download_and_export(
                    dataset_name=job.dataset_name,
                    split=job.split,
                    max_samples=job.max_samples,
                    target_classes=[job.target_class],
                )
            )
        return exported_dirs

    def print_kaggle_candidates(self, max_datasets: int = 5) -> None:
        """Search Kaggle for weak classes without downloading entire datasets."""

        try:
            from miners.kaggle_miner import KaggleMiner

            miner = KaggleMiner()
            for target_class, queries in KAGGLE_QUERY_PLAN.items():
                print(f"\n[KAGGLE] {target_class}")
                for query in queries:
                    try:
                        refs = miner.search(query, max_datasets=max_datasets)
                    except Exception as exc:
                        print(f"[WARN] Kaggle search failed for {query!r}: {exc}")
                        continue
                    for ref in refs:
                        print(f"  - {ref}")
        except Exception as exc:
            print(f"[WARN] Kaggle candidate search unavailable: {exc}")

    @staticmethod
    def _build_fiftyone_jobs(
        max_per_class: int,
        split: str,
        datasets: tuple[str, ...],
    ) -> list[CollectionJob]:
        jobs: list[CollectionJob] = []
        for dataset_name in datasets:
            target_labels = set(SOURCE_CLASS_MAPS[dataset_name].values())
            for target_class in WEAK_TARGET_CLASSES:
                if target_class in target_labels:
                    jobs.append(
                        CollectionJob(
                            dataset_name=dataset_name,
                            split=split,
                            target_class=target_class,
                            max_samples=max_per_class,
                        )
                    )
                else:
                    print(f"[SKIP] {dataset_name} has no mapped label for {target_class}")
        return jobs
