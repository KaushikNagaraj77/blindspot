"""JSONL response cache. Never re-call an API for an input already cached."""

import hashlib
import json
from pathlib import Path


class JsonlCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._mem: dict[str, dict] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._mem[row["key"]] = row["value"]

    @staticmethod
    def key(payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def get(self, payload: dict) -> dict | None:
        return self._mem.get(self.key(payload))

    def put(self, payload: dict, value: dict) -> None:
        k = self.key(payload)
        self._mem[k] = value
        with self.path.open("a") as f:
            f.write(json.dumps({"key": k, "value": value}) + "\n")
