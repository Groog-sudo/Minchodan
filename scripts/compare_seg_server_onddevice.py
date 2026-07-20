#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""서버 YOLO seg vs 온디바이스(Metro 로그) 노면 클래스 혼동 비교.

1) 라이브 구간: Redis risk.events(서버 파이프라인 surface) vs Metro `[Reflex] 전체 탐지`
2) 덤프 JPEG가 있으면 동일 이미지에 서버 segbest.pt를 conf 0.05/0.25/0.35로 재추론

사용:
  # 라이브 로그만 30초 비교
  .venv/bin/python scripts/compare_seg_server_ondevice.py --seconds 30

  # 덤프 프레임 재추론 (SEG_COMPARE_DUMP로 저장된 JPG)
  .venv/bin/python scripts/compare_seg_server_ondevice.py --dump-dir data/seg_compare

환경:
  SEG_COMPARE_DUMP=N  - FastAPI가 cognitive JPEG N장을 data/seg_compare/에 저장
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess  # nosec B404
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

SEG_CLASSES = ("sidewalk_normal", "caution", "roadway", "braille_normal")
CLASS_RE = re.compile(r"\b(sidewalk_normal|caution|roadway|braille_normal)\((0?\.\d+|1(?:\.0+)?)\)")


def _metro_log_path() -> Path | None:
    term_dir = (
        Path.home()
        / ".cursor/projects/Users-kwanbum-Documents-korea-IT-lanhchain-ai-vision-Minchodan/terminals"
    )
    candidates = sorted(term_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            # 최근 파일에서 Reflex 탐지 로그가 있는 것 우선
            text = path.read_text(encoding="utf-8", errors="ignore")[-200_000:]
        except OSError:
            continue
        if "[Reflex] 전체 탐지:" in text:
            return path
    return candidates[0] if candidates else None


def sample_metro(seconds: float) -> Counter:
    path = _metro_log_path()
    counts: Counter = Counter()
    if path is None:
        print("[WARN] Metro 터미널 로그를 찾지 못함")
        return counts
    print(f"[INFO] Metro log: {path}")
    start_size = path.stat().st_size
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            size = path.stat().st_size
            if size > start_size:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    f.seek(start_size)
                    chunk = f.read()
                start_size = size
                for line in chunk.splitlines():
                    if "전체 탐지:" not in line:
                        continue
                    for name, _conf in CLASS_RE.findall(line):
                        counts[name] += 1
        except OSError:
            pass
        time.sleep(0.4)
    return counts


def sample_redis(seconds: float) -> Counter:
    counts: Counter = Counter()
    last_id = "$"
    deadline = time.time() + seconds
    while time.time() < deadline:
        remaining_ms = max(200, int((deadline - time.time()) * 1000))
        try:
            raw = subprocess.check_output(
                [
                    "docker",
                    "exec",
                    "minchodan-redis",
                    "redis-cli",
                    "--raw",
                    "XREAD",
                    "BLOCK",
                    str(min(remaining_ms, 2000)),
                    "COUNT",
                    "80",
                    "STREAMS",
                    "risk.events",
                    last_id,
                ],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=max(3, remaining_ms / 1000 + 1),
            )  # nosec B603 B607
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        if not raw.strip():
            continue
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.count("-") == 1 and ln.split("-")[0].isdigit():
                last_id = ln
                fields: dict[str, str] = {}
                j = i + 1
                while j + 1 < len(lines):
                    k, v = lines[j], lines[j + 1]
                    if k.count("-") == 1 and k.split("-")[0].isdigit():
                        break
                    if k == "risk.events":
                        break
                    fields[k] = v
                    j += 2
                cls = fields.get("class_name", "")
                if cls in SEG_CLASSES:
                    counts[cls] += 1
                i = j
                continue
            i += 1
    return counts


def run_server_seg_on_dump(dump_dir: Path, confs: list[float]) -> None:
    import cv2
    from ultralytics import YOLO

    weights = os.getenv("SEG_COMPARE_WEIGHTS") or os.path.join(
        PROJECT_ROOT, "server/models/yolo26n/segbest.pt"
    )
    images = sorted(dump_dir.glob("*.jpg")) + sorted(dump_dir.glob("*.jpeg"))
    if not images:
        print(f"[WARN] 덤프 이미지 없음: {dump_dir}")
        return
    print(f"[INFO] 서버 seg 재추론: weights={weights}, frames={len(images)}")
    model = YOLO(weights)
    for conf in confs:
        hist: Counter = Counter()
        per_frame_top: list[str] = []
        roadway_frames = 0
        for img_path in images:
            frame = cv2.imread(str(img_path))
            if frame is None:
                continue
            results = model.predict(source=frame, conf=conf, device="cpu", verbose=False)
            r0 = results[0]
            names = r0.names or {}
            frame_classes: list[str] = []
            if r0.boxes is not None and len(r0.boxes) > 0:
                for idx in range(len(r0.boxes)):
                    cls_id = int(r0.boxes.cls[idx])
                    name = names.get(cls_id, str(cls_id))
                    hist[name] += 1
                    frame_classes.append(name)
            if "roadway" in frame_classes:
                roadway_frames += 1
            top = frame_classes[0] if frame_classes else "(none)"
            per_frame_top.append(top)
        print(f"\n=== server seg conf>={conf:.2f} ===")
        for name in SEG_CLASSES:
            print(f"  {name:18s} {hist.get(name, 0)}")
        other = sum(v for k, v in hist.items() if k not in SEG_CLASSES)
        if other:
            print(f"  {'(other)':18s} {other}")
        top_hist = Counter(per_frame_top)
        print(f"  frames_with_roadway={roadway_frames}/{len(images)}")
        print(f"  per-frame top class: {dict(top_hist)}")


def print_side_by_side(server: Counter, ondevice: Counter) -> None:
    print("\n=== LIVE 혼동 비교 (집계) ===")
    print(f"{'class':18s} {'server(Redis)':>14s} {'on-device(Metro)':>16s}")
    for name in SEG_CLASSES:
        print(f"{name:18s} {server.get(name, 0):14d} {ondevice.get(name, 0):16d}")
    s_tot = sum(server.get(n, 0) for n in SEG_CLASSES)
    o_tot = sum(ondevice.get(n, 0) for n in SEG_CLASSES)
    print(f"{'TOTAL':18s} {s_tot:14d} {o_tot:16d}")
    if s_tot and o_tot:
        print(
            "\n해석: 양측 모두 sidewalk 우세·roadway≈0 이면 CoreML 변환 오류보다 "
            "원 가중치/도메인 오분류 가능성이 큼."
        )
        print("서버만 roadway가 많고 온디바이스가 0이면 CoreML 파싱/임계값 쪽을 의심.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=25.0)
    parser.add_argument(
        "--dump-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "data", "seg_compare"),
    )
    parser.add_argument("--skip-live", action="store_true")
    parser.add_argument("--skip-dump-infer", action="store_true")
    args = parser.parse_args()

    print(f"[START] {datetime.now().isoformat(timespec='seconds')}")
    dump_dir = Path(args.dump_dir)

    server_counts: Counter = Counter()
    ondevice_counts: Counter = Counter()
    if not args.skip_live:
        print(f"[INFO] 라이브 샘플링 {args.seconds:.0f}s (Redis + Metro)...")
        # 병렬이 이상적이나 단순화를 위해 Redis를 먼저 짧게, Metro를 같은 구간으로
        # 순차 실행하면 어긋나므로 Metro를 백그라운드 프로세스처럼 인터리브
        deadline = time.time() + args.seconds
        metro_path = _metro_log_path()
        metro_pos = metro_path.stat().st_size if metro_path else 0
        last_id = "$"
        while time.time() < deadline:
            # metro
            if metro_path:
                try:
                    size = metro_path.stat().st_size
                    if size > metro_pos:
                        with metro_path.open("r", encoding="utf-8", errors="ignore") as f:
                            f.seek(metro_pos)
                            chunk = f.read()
                        metro_pos = size
                        for line in chunk.splitlines():
                            if "전체 탐지:" not in line:
                                continue
                            for name, _c in CLASS_RE.findall(line):
                                ondevice_counts[name] += 1
                except OSError:
                    pass
            # redis one shot
            try:
                rem = max(100, int((deadline - time.time()) * 1000))
                raw = subprocess.check_output(
                    [
                        "docker",
                        "exec",
                        "minchodan-redis",
                        "redis-cli",
                        "--raw",
                        "XREAD",
                        "BLOCK",
                        str(min(rem, 800)),
                        "COUNT",
                        "50",
                        "STREAMS",
                        "risk.events",
                        last_id,
                    ],
                    text=True,
                    stderr=subprocess.STDOUT,
                    timeout=3,
                )  # nosec B603 B607
                lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
                i = 0
                while i < len(lines):
                    ln = lines[i]
                    if ln.count("-") == 1 and ln.split("-")[0].isdigit():
                        last_id = ln
                        fields: dict[str, str] = {}
                        j = i + 1
                        while j + 1 < len(lines):
                            k, v = lines[j], lines[j + 1]
                            if k.count("-") == 1 and k.split("-")[0].isdigit():
                                break
                            if k == "risk.events":
                                break
                            fields[k] = v
                            j += 2
                        cls = fields.get("class_name", "")
                        if cls in SEG_CLASSES:
                            server_counts[cls] += 1
                        i = j
                        continue
                    i += 1
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                time.sleep(0.2)
        print_side_by_side(server_counts, ondevice_counts)

    if not args.skip_dump_infer:
        run_server_seg_on_dump(dump_dir, confs=[0.05, 0.25, 0.35])

    print(f"[END] {datetime.now().isoformat(timespec='seconds')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
