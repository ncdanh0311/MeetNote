"""Atomic JSON persistence for completed transcripts and meeting notes."""

import json
from pathlib import Path


def write_result(results_dir: str | Path, job_id: str, minutes: str, transcript: str) -> Path:
    path = Path(results_dir) / f"{job_id}.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"minutes": minutes, "transcript": transcript}, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def read_result(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
