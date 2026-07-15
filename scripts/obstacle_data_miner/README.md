# Obstacle Data Miner

Standalone pipeline for mining external images and exporting 29-class obstacle labels in YOLO format.

## Setup

```powershell
cd obstacle_data_miner
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with Kaggle credentials or configure the official Kaggle `kaggle.json`.

## Model Class Order

The class id order follows the trained AI Hub YOLO detection model used by `object_detection.pt`:

```text
0 barricade, 1 bench, 2 bicycle, 3 bollard, 4 bus, 5 car, 6 carrier, 7 cat,
8 chair, 9 dog, 10 fire_hydrant, 11 kiosk, 12 motorcycle, 13 movable_signage,
14 parking_meter, 15 person, 16 pole, 17 potted_plant, 18 power_controller,
19 scooter, 20 stop, 21 stroller, 22 table, 23 traffic_light,
24 traffic_light_controller, 25 traffic_sign, 26 tree_trunk, 27 truck,
28 wheelchair
```

## Commands

```powershell
python main.py collect-weak --max-per-class 100 --dataset coco-2017
python main.py collect-weak --max-per-class 100 --dataset open-images-v7
python main.py collect-weak --kaggle-search
python main.py kaggle "fire hydrant object detection" --max 1
python main.py fiftyone --dataset open-images-v7 --max 100 --only-class chair
python main.py plan --class bollard
python main.py label --source datasets/object_detection/raw --model yolo26n.pt --confidence 0.35
```

Object Detection YOLO assets are written to:

- `datasets/object_detection/images`
- `datasets/object_detection/labels`

The shared `datasets/object_detection/hash_index.json` file stores perceptual hashes used to skip near-duplicate images.

By default, auto-labeling uses `yolo26n.pt`. Override it with `DEFAULT_MODEL` in `.env` or with the `--model` CLI option.

## API-Only Weak-Class Collection

For the current weak classes, use `collect-weak` first. It avoids search-engine crawling and only downloads annotation-backed samples through FiftyOne:

- COCO/Open Images covered: `bench`, `chair`, `table`, `fire_hydrant`
- Not reliably covered by those taxonomies: `scooter`, `carrier`, `kiosk`

For uncovered classes, run Kaggle candidate search first and inspect dataset names before downloading:

```powershell
python main.py collect-weak --kaggle-search
```

Use `requirements_api.txt` when you only want stable dataset APIs:

```powershell
.\.venv\Scripts\pip install -r requirements_api.txt
```

Web crawling is not part of the default collection path. Only use `scrape` or `scrape-class` when a specific URL/domain collection target has been approved.

## Dataset Areas

Object Detection and Segmentation data are intentionally separated:

```text
datasets/
  object_detection/
    images/
    labels/
    raw/
    fiftyone_exports/
    external_exports/
  segmentation/
    images/
    labels/
    masks/
    raw/
    external_exports/
```

Detection labels are YOLO bbox text files. Segmentation labels must be YOLO polygon text files.

## Class-Aware Collection

Use the built-in 29-class collection policy before scraping. It records what to include, what to exclude, and which near-miss classes should be treated as hard negatives.

```powershell
python main.py plan
python main.py plan --class traffic_light_controller --export datasets/collection_plan.csv
python main.py scrape-class traffic_light_controller --max-per-query 50 --engine bing
python main.py label --source datasets/object_detection/raw/web --only-class traffic_light_controller
```

When a class is confused with another class, collect both the positive target and the hard-negative neighbor. For example, collect `bollard`, then also inspect `pole` and `tree_trunk` samples so mislabeled boxes do not enter the final training set.

## Result Analysis

Analyze per-class prediction folders from `scripts/run_test_per_class.py`:

```powershell
python utils/analyze_yolo_results.py "C:\dev_task\workspace\Project\finally_project\AI_GilDang\Minchodan\data\test_100_samples\results" --output datasets/hallucination_report.md
```
