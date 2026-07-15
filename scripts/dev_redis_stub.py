# -*- coding: utf-8 -*-
import socketserver
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _simple(value: str) -> bytes:
    return f"+{value}\r\n".encode("utf-8")


def _error(value: str) -> bytes:
    return f"-ERR {value}\r\n".encode("utf-8")


def _integer(value: int) -> bytes:
    return f":{value}\r\n".encode("utf-8")


def _bulk(value: str | bytes | None) -> bytes:
    if value is None:
        return b"$-1\r\n"
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return b"$" + str(len(data)).encode("ascii") + b"\r\n" + data + b"\r\n"


def _array(values: list[bytes] | None) -> bytes:
    if values is None:
        return b"*-1\r\n"
    return b"*" + str(len(values)).encode("ascii") + b"\r\n" + b"".join(values)


class RedisStubState:
    def __init__(self) -> None:
        # key -> (value, expire_at_monotonic | None)
        self.kv: dict[str, tuple[str, float | None]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.stream_seq = 0

    def _purge_expired(self, key: str) -> None:
        entry = self.kv.get(key)
        if entry is None:
            return
        _, expire_at = entry
        if expire_at is not None and time.monotonic() >= expire_at:
            del self.kv[key]

    def get(self, key: str) -> str | None:
        self._purge_expired(key)
        entry = self.kv.get(key)
        return None if entry is None else entry[0]

    def set(self, key: str, value: str, ttl_seconds: float | None = None) -> None:
        expire_at = None if ttl_seconds is None else time.monotonic() + float(ttl_seconds)
        self.kv[key] = (value, expire_at)

    def exists(self, key: str) -> bool:
        self._purge_expired(key)
        return key in self.kv

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            self._purge_expired(key)
            if key in self.kv:
                del self.kv[key]
                deleted += 1
            if key in self.hashes:
                del self.hashes[key]
                deleted += 1
        return deleted

    def ttl(self, key: str) -> int:
        self._purge_expired(key)
        entry = self.kv.get(key)
        if entry is None:
            return -2
        _, expire_at = entry
        if expire_at is None:
            return -1
        remaining = int(expire_at - time.monotonic())
        return max(0, remaining)

    def keys(self, pattern: str) -> list[str]:
        # 개발 스텁은 와일드카드 '*' 접미사만 최소 지원 (예: suppress:*)
        prefix = pattern[:-1] if pattern.endswith("*") else None
        matched: list[str] = []
        for key in list(self.kv.keys()):
            self._purge_expired(key)
            if key not in self.kv:
                continue
            if prefix is None:
                if key == pattern:
                    matched.append(key)
            elif key.startswith(prefix):
                matched.append(key)
        return matched


STATE = RedisStubState()


class RedisStubHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        while True:
            try:
                command = self._read_command()
                if not command:
                    return
                response = self._dispatch(command)
                self.request.sendall(response)
            except ConnectionError:
                return
            except Exception as exc:
                self.request.sendall(_error(str(exc)))

    def _readline(self) -> bytes:
        data = bytearray()
        while True:
            chunk = self.request.recv(1)
            if not chunk:
                raise ConnectionError
            data.extend(chunk)
            if data.endswith(b"\r\n"):
                return bytes(data[:-2])

    def _read_command(self) -> list[str]:
        first = self._readline()
        if not first:
            return []
        if first.startswith(b"*"):
            count = int(first[1:])
            parts: list[str] = []
            for _ in range(count):
                length_line = self._readline()
                if not length_line.startswith(b"$"):
                    raise ValueError("invalid bulk length")
                length = int(length_line[1:])
                data = b""
                while len(data) < length:
                    chunk = self.request.recv(length - len(data))
                    if not chunk:
                        raise ConnectionError
                    data += chunk
                _ = self.request.recv(2)
                parts.append(data.decode("utf-8", errors="replace"))
            return parts
        return first.decode("utf-8", errors="replace").split()

    def _dispatch(self, command: list[str]) -> bytes:
        name = command[0].upper()
        if name in {"PING"}:
            return _simple("PONG")
        if name in {"CLIENT", "HELLO", "AUTH", "SELECT"}:
            return _simple("OK")
        if name == "SET":
            # SET key value [EX seconds] ...
            if len(command) >= 3:
                ttl: float | None = None
                extras = [part.upper() for part in command[3:]]
                if "EX" in extras:
                    ex_idx = extras.index("EX")
                    if ex_idx + 1 < len(command[3:]):
                        ttl = float(command[3:][ex_idx + 1])
                STATE.set(command[1], command[2], ttl_seconds=ttl)
            return _simple("OK")
        if name == "GET":
            return _bulk(STATE.get(command[1]))
        if name == "SETEX":
            # SETEX key seconds value
            if len(command) >= 4:
                STATE.set(command[1], command[3], ttl_seconds=float(command[2]))
            return _simple("OK")
        if name == "EXISTS":
            # EXISTS key [key ...] -> 존재하는 키 개수 (정수)
            count = sum(1 for key in command[1:] if STATE.exists(key))
            return _integer(count)
        if name == "DEL":
            return _integer(STATE.delete(*command[1:]))
        if name == "TTL":
            return _integer(STATE.ttl(command[1]) if len(command) >= 2 else -2)
        if name == "KEYS":
            pattern = command[1] if len(command) >= 2 else "*"
            values = [_bulk(key) for key in STATE.keys(pattern)]
            return _array(values)
        if name == "EXPIRE":
            if len(command) >= 3 and STATE.exists(command[1]):
                value = STATE.get(command[1])
                if value is not None:
                    STATE.set(command[1], value, ttl_seconds=float(command[2]))
                    return _integer(1)
            return _integer(0)
        if name == "HSET":
            key = command[1]
            bucket = STATE.hashes.setdefault(key, {})
            added = 0
            for idx in range(2, len(command) - 1, 2):
                if command[idx] not in bucket:
                    added += 1
                bucket[command[idx]] = command[idx + 1]
            return _integer(added)
        if name == "HGETALL":
            bucket = STATE.hashes.get(command[1], {})
            values: list[bytes] = []
            for key, value in bucket.items():
                values.append(_bulk(key))
                values.append(_bulk(value))
            return _array(values)
        if name == "XADD":
            STATE.stream_seq += 1
            event_id = f"{int(time.time() * 1000)}-{STATE.stream_seq}"
            return _bulk(event_id)
        if name in {"XREAD", "XREADGROUP"}:
            return _array(None)
        if name in {"XGROUP", "ACK", "XACK"}:
            return _simple("OK")
        # 미구현 명령은 단순 OK 대신 에러를 주어, EXISTS처럼 정수 응답을 기대하는
        # 클라이언트가 bool("OK")==True로 오판하는 일을 막는다.
        return _error(f"unsupported command '{name}'")


class ThreadedRedisStub(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    with ThreadedRedisStub(("127.0.0.1", 6379), RedisStubHandler) as server:
        print("[dev_redis_stub] listening on 127.0.0.1:6379", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
