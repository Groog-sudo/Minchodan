"""CLI entrypoint for external data mining and auto-labeling."""

from __future__ import annotations

import argparse
from pathlib import Path

from class_specs import CLASS_SPECS, get_class_spec, validate_specs
from config import SETTINGS
from utils.collection_plan import export_plan, print_plan


def build_parser() -> argparse.ArgumentParser:
    # 💡 [면접 대비 주석]
    # Q: 데이터 파이프라인(장애물 마이너)을 별도의 CLI 툴로 독립적으로 개발한 이유는 무엇인가요?
    # A: 시각장애인 보행 환경에는 '볼라드(Bollard)'나 '키오스크(Kiosk)' 같은 특수 클래스가 많은데,
    #    COCO 등 공개 데이터셋만으로는 데이터가 턱없이 부족한 'Long-tail 문제'가 발생했습니다.
    #    이를 해결하기 위해 Kaggle, OpenImages(FiftyOne), 웹 크롤링(Scraping) 등 다양한 소스에서
    #    부족한 이미지를 자동으로 긁어오고(Mining) 오토라벨링까지 수행하는 일원화된 파이프라인이 필요했습니다.
    parser = argparse.ArgumentParser(description="Mine and auto-label obstacle images.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    kaggle = subparsers.add_parser("kaggle", help="Search/download Kaggle datasets.")
    kaggle.add_argument("query", help="Kaggle dataset search query.")
    kaggle.add_argument("--max", type=int, default=3, help="Maximum datasets to download.")

    fiftyone = subparsers.add_parser("fiftyone", help="Download Open Images/COCO samples.")
    fiftyone.add_argument(
        "--dataset", choices=["open-images-v7", "coco-2017"], default="open-images-v7"
    )
    fiftyone.add_argument("--split", default="validation")
    fiftyone.add_argument("--max", type=int, default=500, help="Maximum samples to download.")
    fiftyone.add_argument(
        "--only-class",
        action="append",
        default=[],
        help="Target class name to download. Repeatable.",
    )

    # 💡 [면접 대비 주석]
    # Q: Kaggle, FiftyOne, 웹 크롤링 등 다양한 소스를 혼합(Multi-source)한 이유는?
    # A: 한국의 보행 환경(점자블록, 한국형 볼라드, 전동 킥보드 등)은 글로벌 데이터와 형태가 다릅니다.
    #    1차로 COCO/OpenImages에서 글로벌 범용 데이터를 확보하고, 2차로 국내 AIHub 데이터와 웹 크롤링을 통해
    #    Domain Gap(도메인 격차)을 메꾸는 전략을 취했습니다.
    collect_weak = subparsers.add_parser(
        "collect-weak", help="API-only collection for weak classes."
    )
    collect_weak.add_argument("--max-per-class", type=int, default=100)
    collect_weak.add_argument("--split", default="validation")
    collect_weak.add_argument(
        "--dataset",
        action="append",
        choices=["open-images-v7", "coco-2017"],
        default=[],
        help="FiftyOne dataset to use. Repeatable. Defaults to both COCO and Open Images.",
    )
    collect_weak.add_argument(
        "--kaggle-search",
        action="store_true",
        help="Search Kaggle candidates for weak classes without downloading them.",
    )

    scrape = subparsers.add_parser("scrape", help="Crawl web images for a keyword.")
    scrape.add_argument("keyword", help="Image search keyword.")
    scrape.add_argument("--max", type=int, default=100, help="Maximum images to download.")
    scrape.add_argument("--headless", action="store_true", help="Run Selenium headless.")
    scrape.add_argument("--engine", choices=["bing", "google"], default="bing")

    scrape_class = subparsers.add_parser(
        "scrape-class", help="Crawl all curated queries for a target class."
    )
    scrape_class.add_argument("target_class", help="Class id or class name, e.g. 15 or bollard.")
    scrape_class.add_argument("--max-per-query", type=int, default=50)
    scrape_class.add_argument("--headless", action="store_true", help="Run Selenium headless.")
    scrape_class.add_argument("--engine", choices=["bing", "google"], default="bing")

    label = subparsers.add_parser("label", help="Auto-label raw images into YOLO format.")
    label.add_argument(
        "--source", type=Path, default=SETTINGS.raw_root, help="Raw image directory."
    )
    label.add_argument(
        "--model", default=SETTINGS.default_model, help="Ultralytics YOLO 26n model path/name."
    )
    label.add_argument("--confidence", type=float, default=SETTINGS.min_confidence)
    label.add_argument(
        "--only-class",
        action="append",
        default=[],
        help="Keep only the given class id/name. Repeatable.",
    )

    plan = subparsers.add_parser("plan", help="Print/export 29-class collection policy.")
    plan.add_argument("--class", dest="target_class", help="Class id or class name to inspect.")
    plan.add_argument("--export", type=Path, help="Export plan as .csv or .json.")

    return parser


def main() -> None:
    validate_specs()
    SETTINGS.ensure_directories()
    args = build_parser().parse_args()

    if args.command == "kaggle":
        from miners.kaggle_miner import KaggleMiner

        KaggleMiner().search_and_download(args.query, max_datasets=args.max)
    elif args.command == "fiftyone":
        from miners.fiftyone_miner import FiftyOneMiner

        FiftyOneMiner().download_and_export(
            dataset_name=args.dataset,
            split=args.split,
            max_samples=args.max,
            target_classes=args.only_class,
        )
    elif args.command == "collect-weak":
        from miners.api_dataset_collector import APIDatasetCollector

        collector = APIDatasetCollector()
        collector.collect_weak_classes(
            max_per_class=args.max_per_class,
            split=args.split,
            datasets=tuple(args.dataset) if args.dataset else ("coco-2017", "open-images-v7"),
        )
        if args.kaggle_search:
            collector.print_kaggle_candidates()
    elif args.command == "scrape":
        from miners.web_scraper import WebScraper

        scraper = WebScraper(headless=args.headless)
        if args.engine == "google":
            scraper.scrape_google_images(args.keyword, max_images=args.max)
        else:
            scraper.scrape_bing_images(args.keyword, max_images=args.max)
    elif args.command == "scrape-class":
        from miners.web_scraper import WebScraper

        spec = get_class_spec(args.target_class)
        scraper = WebScraper(headless=args.headless)
        for query in spec.search_queries:
            print(f"Collecting [{spec.class_id}] {spec.name}: {query}")
            if args.engine == "google":
                scraper.scrape_google_images(query, max_images=args.max_per_query)
            else:
                scraper.scrape_bing_images(query, max_images=args.max_per_query)
    elif args.command == "label":
        from labelers.auto_labeler import AutoLabeler

        allowed_classes = [get_class_spec(item).name for item in args.only_class]
        AutoLabeler(
            model_name=args.model, confidence=args.confidence, allowed_classes=allowed_classes
        ).label_directory(args.source)
    elif args.command == "plan":
        specs = (
            [get_class_spec(args.target_class)] if args.target_class else list(CLASS_SPECS.values())
        )
        print_plan(specs)
        if args.export:
            print(f"Exported plan to {export_plan(args.export, specs)}")


if __name__ == "__main__":
    main()
