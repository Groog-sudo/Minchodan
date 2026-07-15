"""Kaggle dataset search/download helpers."""

from __future__ import annotations

import zipfile
from pathlib import Path

from config import SETTINGS
from utils.format_converter import FormatConverter


class KaggleMiner:
    """Download public Kaggle datasets and convert common annotations to YOLO."""

    def __init__(self, download_root: Path | None = None) -> None:
        self.download_root = download_root or SETTINGS.raw_root / "kaggle"
        self.download_root.mkdir(parents=True, exist_ok=True)
        self.converter = FormatConverter()

    def _client(self):
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
        except ImportError as exc:
            raise RuntimeError("Install kaggle first: pip install kaggle") from exc

        api = KaggleApi()
        api.authenticate()
        return api

    def search(self, query: str, max_datasets: int = 5) -> list[str]:
        api = self._client()
        datasets = api.dataset_list(search=query, sort_by="hottest")
        refs = [dataset.ref for dataset in datasets[:max_datasets]]
        print(f"Found {len(refs)} Kaggle datasets for query={query!r}: {refs}")
        return refs

    def search_and_download(self, query: str, max_datasets: int = 3) -> list[Path]:
        downloaded: list[Path] = []
        for dataset_ref in self.search(query, max_datasets=max_datasets):
            target_dir = self.download_root / dataset_ref.replace("/", "__")
            target_dir.mkdir(parents=True, exist_ok=True)
            try:
                self._client().dataset_download_files(dataset_ref, path=str(target_dir), quiet=False)
                self._extract_archives(target_dir)
                self.converter.convert_dataset_annotations(target_dir)
                downloaded.append(target_dir)
            except Exception as exc:
                print(f"[WARN] Skipping Kaggle dataset {dataset_ref}: {exc}")
        return downloaded

    @staticmethod
    def _extract_archives(directory: Path) -> None:
        for archive in directory.glob("*.zip"):
            try:
                with zipfile.ZipFile(archive) as zip_file:
                    zip_file.extractall(directory / archive.stem)
            except zipfile.BadZipFile:
                print(f"[WARN] Bad zip skipped: {archive}")
