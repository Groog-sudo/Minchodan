# -*- coding: utf-8 -*-
"""로컬 전용 보안 비밀값을 생성하고 .env 파일 권한을 제한한다."""

import os
import secrets
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = SCRIPT_DIR.parent
ROOT_ENV = PROJECT_ROOT / ".env"
CLIENT_ENV = PROJECT_ROOT / "client" / ".env"

KNOWN_INSECURE_VALUES = {
    "",
    "change-me",
    "dev-secret-key-change-in-production",
    "minchodan_password",
    "minchodan_root_password",
    "token-abc-001",
    "token-abc-002",
}


def _read_env(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return lines, values


def _write_env(path: Path, updates: dict[str, str]) -> list[str]:
    if path.is_symlink():
        raise RuntimeError(f"심볼릭 링크 환경 파일은 수정하지 않습니다: {path}")
    lines, _ = _read_env(path)
    pending = dict(updates)
    output: list[str] = []
    changed: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in pending:
                replacement = f"{key}={pending.pop(key)}"
                output.append(replacement)
                if replacement != line:
                    changed.append(key)
                continue
        output.append(line)

    if pending:
        if output and output[-1] != "":
            output.append("")
        output.append("# --- 자동 생성 보안 설정 (로컬 전용) ---")
        for key, value in pending.items():
            output.append(f"{key}={value}")
            changed.append(key)

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    file_descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as env_file:
            env_file.write("\n".join(output).rstrip() + "\n")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
    path.chmod(0o600)
    return changed


def _secure_value(current: str | None, byte_count: int = 32) -> str:
    if current and current not in KNOWN_INSECURE_VALUES and len(current) >= 32:
        return current
    return secrets.token_urlsafe(byte_count)


def main() -> int:
    _, root_values = _read_env(ROOT_ENV)
    _, client_values = _read_env(CLIENT_ENV)
    app_env = root_values.get("APP_ENV", "development").strip().lower()

    jwt_secret = _secure_value(root_values.get("JWT_SECRET_KEY"), 48)
    bootstrap_token = _secure_value(root_values.get("ADMIN_BOOTSTRAP_TOKEN"), 32)
    redis_password = _secure_value(root_values.get("REDIS_PASSWORD"), 32)
    db_password = _secure_value(root_values.get("COMPOSE_DB_PASSWORD"), 32)
    db_root_password = _secure_value(root_values.get("COMPOSE_DB_ROOT_PASSWORD"), 40)
    device_id = (
        client_values.get("EXPO_PUBLIC_DEVICE_ID", "").strip() or f"dev-{secrets.token_hex(4)}"
    )
    device_token = _secure_value(client_values.get("EXPO_PUBLIC_DEVICE_TOKEN"), 32)

    root_updates = {
        "JWT_SECRET_KEY": jwt_secret,
        "ADMIN_BOOTSTRAP_TOKEN": bootstrap_token,
        "REDIS_PASSWORD": redis_password,
        "REDIS_URL": f"redis://:{redis_password}@localhost:6379",
        "COMPOSE_DB_PASSWORD": db_password,
        "COMPOSE_DB_ROOT_PASSWORD": db_root_password,
        "ALLOW_STATIC_DEVICE_TOKENS": "false" if app_env == "production" else "true",
        "DEVICE_STATIC_TOKENS": "" if app_env == "production" else f"{device_id}:{device_token}",
        "ENABLE_DEBUG_API": "false",
        "ENABLE_NAVIGATION_SIMULATOR": "false",
    }
    client_updates = {
        "EXPO_PUBLIC_DEVICE_ID": device_id,
        "EXPO_PUBLIC_DEVICE_TOKEN": device_token,
        "EXPO_PUBLIC_WS_SCHEME": "wss",
    }

    changed = _write_env(ROOT_ENV, root_updates)
    changed += [f"client:{key}" for key in _write_env(CLIENT_ENV, client_updates)]
    for optional_env in (PROJECT_ROOT / "console" / ".env",):
        if optional_env.exists():
            optional_env.chmod(0o600)

    changed_names = ", ".join(changed) if changed else "없음"
    print(f"보안 설정 완료. 변경된 키: {changed_names}")
    print("비밀값은 출력하지 않았으며 .env 파일 권한을 600으로 제한했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
