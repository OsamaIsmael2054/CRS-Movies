import json
from pathlib import Path
from typing import Iterator


def read_json(path: str | Path) -> dict:
    """Load a JSON object file (e.g. item_map.json, user_ids.json)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def iter_jsonl(path: str | Path) -> Iterator[dict]:
    """Yield each line of a JSONL file as a parsed dict (streaming)."""
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
