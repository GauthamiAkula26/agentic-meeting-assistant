from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

DB_PATH = Path("storage/meetings_db.json")

def ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        DB_PATH.write_text("[]", encoding="utf-8")

def load_meetings() -> List[Dict[str, Any]]:
    ensure_db()
    try:
        return json.loads(DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_meetings(meetings: List[Dict[str, Any]]) -> None:
    ensure_db()
    DB_PATH.write_text(json.dumps(meetings, indent=2, ensure_ascii=False), encoding="utf-8")

def upsert_meeting(meeting: Dict[str, Any]) -> None:
    meetings = load_meetings()
    updated = False
    for idx, item in enumerate(meetings):
        if item.get("meeting_id") == meeting.get("meeting_id"):
            meetings[idx] = meeting
            updated = True
            break
    if not updated:
        meetings.append(meeting)
    save_meetings(meetings)

def delete_meeting(meeting_id: str) -> None:
    meetings = [m for m in load_meetings() if m.get("meeting_id") != meeting_id]
    save_meetings(meetings)
