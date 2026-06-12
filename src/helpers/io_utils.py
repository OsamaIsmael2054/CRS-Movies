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


def parse_conversations(path: str | Path) -> dict[int, str]:
    """Parse Conversation.txt into {conversation_id: dialogue_text}.

    Blocks are delimited by lines containing only a conversation id (digits);
    everything until the next such line is that conversation's dialogue.
    """
    dialogues: dict[int, str] = {}
    current_id: int | None = None
    buffer: list[str] = []

    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.isdigit():
                if current_id is not None:
                    dialogues[current_id] = "".join(buffer).strip()
                current_id = int(stripped)
                buffer = []
            else:
                buffer.append(line)

    if current_id is not None:
        dialogues[current_id] = "".join(buffer).strip()

    return dialogues
