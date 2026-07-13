# -*- coding: utf-8 -*-
import socketserver
import sys
import time
from typing import Any

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
        self.kv: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.stream_seq = 0


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
            if len(command) >= 3:
                STATE.kv[command[1]] = command[2]
            return _simple("OK")
        if name == "GET":
            return _bulk(STATE.kv.get(command[1]))
        if name == "SETEX":
            if len(command) >= 4:
                STATE.kv[command[1]] = command[3]
            return _simple("OK")
        if name == "EXPIRE":
            return _integer(1)
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
        return _simple("OK")


class ThreadedRedisStub(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    with ThreadedRedisStub(("127.0.0.1", 6379), RedisStubHandler) as server:
        print("[dev_redis_stub] listening on 127.0.0.1:6379", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
