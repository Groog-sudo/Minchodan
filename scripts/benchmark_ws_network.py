"""
WebSocket 네트워크 RTT 벤치마크 스크립트.

ngrok, Tailscale, LAN 등 여러 /ws/detect 주소에 같은 network_probe 메시지를 보내
순수 WebSocket 왕복 지연을 비교합니다.
"""

import argparse
import asyncio
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path
from types import ModuleType
from urllib.parse import quote, urlparse

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def parse_target(raw_target: str) -> tuple[str, str]:
    """label=ws_url 형식의 타깃 인자를 파싱합니다."""
    if "=" not in raw_target:
        raise argparse.ArgumentTypeError(
            "--target 값은 label=ws://host/ws/detect 형식이어야 합니다."
        )
    label, url = raw_target.split("=", 1)
    label = label.strip()
    url = url.strip()
    parsed = urlparse(url)
    if not label:
        raise argparse.ArgumentTypeError("target label은 비워둘 수 없습니다.")
    if parsed.scheme not in {"ws", "wss"}:
        raise argparse.ArgumentTypeError("target URL은 ws:// 또는 wss:// 로 시작해야 합니다.")
    if not parsed.netloc:
        raise argparse.ArgumentTypeError("target URL에 host가 없습니다.")
    return label, url.rstrip("/")


def percentile(values: list[float], percentile_value: float) -> float:
    """선형 보간으로 분위수를 계산합니다."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * percentile_value / 100.0
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index
    return sorted_values[lower_index] * (1.0 - weight) + sorted_values[upper_index] * weight


def load_websockets_module() -> ModuleType:
    """websockets 의존성을 실제 측정 시점에 로드합니다."""
    try:
        import websockets
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "websockets 패키지가 필요합니다. 프로젝트 루트에서 "
            "`python3 -m pip install -r requirements.txt` 실행 후 다시 측정하세요."
        ) from error
    return websockets


def summarize(
    label: str, url: str, rtt_values: list[float], failures: int, handshake_ms: float
) -> dict:
    """타깃별 RTT 샘플을 요약합니다."""
    sample_count = len(rtt_values)
    return {
        "label": label,
        "url": url,
        "samples": sample_count,
        "failures": failures,
        "handshake_ms": round(handshake_ms, 2),
        "min_ms": round(min(rtt_values), 2) if rtt_values else 0.0,
        "avg_ms": round(statistics.fmean(rtt_values), 2) if rtt_values else 0.0,
        "p50_ms": round(percentile(rtt_values, 50), 2),
        "p95_ms": round(percentile(rtt_values, 95), 2),
        "max_ms": round(max(rtt_values), 2) if rtt_values else 0.0,
        "stdev_ms": round(statistics.pstdev(rtt_values), 2) if sample_count > 1 else 0.0,
    }


async def recv_probe_ack(ws, probe_id: str, timeout_s: float) -> dict:
    """하트비트 메시지를 처리하면서 특정 probe ack를 기다립니다."""
    deadline = time.perf_counter() + timeout_s
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError(f"probe timeout: {probe_id}")
        raw_message = await asyncio.wait_for(ws.recv(), timeout=remaining)
        if not isinstance(raw_message, str):
            continue
        data = json.loads(raw_message)
        message_type = data.get("type")
        if message_type == "heartbeat":
            await ws.send(json.dumps({"type": "heartbeat_ack", "ts": time.time() * 1000}))
            continue
        if message_type == "ping":
            await ws.send(json.dumps({"type": "pong", "ts": time.time() * 1000}))
            continue
        if message_type == "network_probe_ack" and data.get("probe_id") == probe_id:
            return data


async def authenticate(ws, device_id: str, token: str, timeout_s: float) -> float:
    """welcome 수신 후 hello/auth_ok까지의 핸드셰이크 시간을 측정합니다."""
    handshake_start = time.perf_counter()
    raw_welcome = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
    welcome = json.loads(raw_welcome)
    if welcome.get("type") != "welcome":
        raise RuntimeError(f"unexpected welcome message: {welcome}")

    await ws.send(json.dumps({"type": "hello", "device_id": device_id, "token": token}))
    raw_auth = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
    auth = json.loads(raw_auth)
    if auth.get("type") != "auth_ok":
        raise RuntimeError(f"authentication failed or unexpected message: {auth}")
    return (time.perf_counter() - handshake_start) * 1000.0


async def run_target(
    websockets_module: ModuleType,
    label: str,
    url: str,
    device_id: str,
    token: str,
    count: int,
    warmup: int,
    interval_ms: int,
    payload_bytes: int,
    timeout_s: float,
) -> tuple[dict, list[dict]]:
    """한 타깃에 대해 probe RTT 샘플을 수집합니다."""
    target_url = f"{url}?device_id={quote(device_id)}"
    payload = "x" * payload_bytes
    samples: list[dict] = []
    rtt_values: list[float] = []
    failures = 0

    async with websockets_module.connect(
        target_url, open_timeout=timeout_s, close_timeout=1.0
    ) as ws:
        handshake_ms = await authenticate(ws, device_id, token, timeout_s)
        total_iterations = warmup + count
        for sample_index in range(total_iterations):
            probe_id = f"{label}-{int(time.time() * 1000)}-{sample_index}"
            sent_at = time.perf_counter()
            await ws.send(
                json.dumps(
                    {
                        "type": "network_probe",
                        "probe_id": probe_id,
                        "client_label": label,
                        "client_sent_ts": time.time() * 1000,
                        "payload": payload,
                    }
                )
            )
            try:
                ack = await recv_probe_ack(ws, probe_id, timeout_s)
                rtt_ms = (time.perf_counter() - sent_at) * 1000.0
            except (TimeoutError, websockets_module.WebSocketException, json.JSONDecodeError):
                failures += 1
                await asyncio.sleep(interval_ms / 1000.0)
                continue

            if sample_index >= warmup:
                rounded_rtt = round(rtt_ms, 2)
                rtt_values.append(rounded_rtt)
                samples.append(
                    {
                        "label": label,
                        "url": url,
                        "probe_id": probe_id,
                        "rtt_ms": rounded_rtt,
                        "payload_bytes": ack.get("payload_bytes", payload_bytes),
                        "server_received_ts": ack.get("server_received_ts"),
                        "server_sent_ts": ack.get("server_sent_ts"),
                    }
                )
            await asyncio.sleep(interval_ms / 1000.0)

    return summarize(label, url, rtt_values, failures, handshake_ms), samples


def print_summary(summaries: list[dict]) -> None:
    """벤치마크 요약을 표 형태로 출력합니다."""
    print("\nWebSocket network_probe RTT 결과")
    print("-" * 102)
    print(
        f"{'label':<14} {'samples':>7} {'fail':>5} {'handshake':>10} "
        f"{'avg':>8} {'p50':>8} {'p95':>8} {'max':>8} {'improve':>10}"
    )
    print("-" * 102)
    baseline_avg = summaries[0]["avg_ms"] if summaries else 0.0
    for summary in summaries:
        improvement = ""
        if baseline_avg > 0 and summary is not summaries[0]:
            improvement_value = (baseline_avg - summary["avg_ms"]) / baseline_avg * 100.0
            improvement = f"{improvement_value:+.1f}%"
        print(
            f"{summary['label']:<14} {summary['samples']:>7} {summary['failures']:>5} "
            f"{summary['handshake_ms']:>10.2f} {summary['avg_ms']:>8.2f} "
            f"{summary['p50_ms']:>8.2f} {summary['p95_ms']:>8.2f} "
            f"{summary['max_ms']:>8.2f} {improvement:>10}"
        )
    print("-" * 102)
    print("improve는 첫 번째 --target 평균 RTT 대비 개선율입니다.")


def write_csv(path: Path, samples: list[dict]) -> None:
    """개별 probe 샘플을 CSV로 저장합니다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "label",
        "url",
        "probe_id",
        "rtt_ms",
        "payload_bytes",
        "server_received_ts",
        "server_sent_ts",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)


async def async_main(args: argparse.Namespace) -> int:
    """CLI 비동기 엔트리포인트."""
    token = args.token or os.getenv("EXPO_PUBLIC_DEVICE_TOKEN") or os.getenv("DEVICE_TOKEN")
    if not token:
        print("--token 또는 EXPO_PUBLIC_DEVICE_TOKEN 환경 변수가 필요합니다.", file=sys.stderr)
        return 2

    summaries: list[dict] = []
    all_samples: list[dict] = []
    try:
        websockets_module = load_websockets_module()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    for label, url in args.target:
        try:
            summary, samples = await run_target(
                websockets_module=websockets_module,
                label=label,
                url=url,
                device_id=args.device_id,
                token=token,
                count=args.count,
                warmup=args.warmup,
                interval_ms=args.interval_ms,
                payload_bytes=args.payload_bytes,
                timeout_s=args.timeout_s,
            )
        except (
            OSError,
            TimeoutError,
            RuntimeError,
            websockets_module.WebSocketException,
            json.JSONDecodeError,
        ) as error:
            print(f"[{label}] 측정 실패: {error}", file=sys.stderr)
            summaries.append(
                {
                    "label": label,
                    "url": url,
                    "samples": 0,
                    "failures": args.count,
                    "handshake_ms": 0.0,
                    "min_ms": 0.0,
                    "avg_ms": 0.0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "max_ms": 0.0,
                    "stdev_ms": 0.0,
                }
            )
            continue
        summaries.append(summary)
        all_samples.extend(samples)

    print_summary(summaries)

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                {"summaries": summaries, "samples": all_samples}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
    if args.csv_out:
        write_csv(Path(args.csv_out), all_samples)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서를 구성합니다."""
    parser = argparse.ArgumentParser(
        description="ngrok/Tailscale/LAN WebSocket RTT를 network_probe로 비교합니다."
    )
    parser.add_argument(
        "--target",
        action="append",
        type=parse_target,
        required=True,
        help="label=ws://host:8000/ws/detect 또는 label=wss://domain/ws/detect 형식입니다.",
    )
    parser.add_argument("--device-id", default=os.getenv("EXPO_PUBLIC_DEVICE_ID", "dev-001"))
    parser.add_argument("--token", default=None)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--interval-ms", type=int, default=200)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--timeout-s", type=float, default=5.0)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--csv-out", default=None)
    return parser


def main() -> int:
    """동기 CLI 엔트리포인트."""
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
