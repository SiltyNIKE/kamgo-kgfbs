# Duplicate detection and event state management.
# SQLite for live/initial mode (persisted between runs), in-memory dict for mock.

import sqlite3
import json
import os

DB_PATH = os.getenv("KGFBS_DB_PATH", "kgfbs_events.db")

_mock_db: dict[str, dict] = {}
_mock_review_queue: list = []
_use_mock = False

# Single shared connection for the entire run – avoids thousands of open/close
# operations when processing 40k events (4000 pages × ~10 events each).
_conn: sqlite3.Connection | None = None


def init_db(mock: bool = False):
    global _use_mock, _conn
    _use_mock = mock
    if not mock:
        _conn = sqlite3.connect(DB_PATH)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                fb_id TEXT PRIMARY KEY,
                start_at TEXT,
                data TEXT,
                scraped_at TEXT
            )
        """)
        # review_queue holds events for human review:
        # - AI-categorized events (reviewer can correct → used as few-shot examples)
        # - Events where startAt changed (reviewer verifies it's intentional)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS review_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fb_id TEXT,
                name TEXT,
                reason TEXT,
                ai_category TEXT,
                original_category TEXT,
                reviewed INTEGER DEFAULT 0,
                correct_category TEXT,
                created_at TEXT
            )
        """)
        _conn.commit()


def close_db():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def _get_conn() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("DB not initialized – call init_db() first")
    return _conn


def is_duplicate(event: dict) -> bool:
    fb_id = event.get("fbId")
    if _use_mock:
        return fb_id in _mock_db
    row = _get_conn().execute("SELECT 1 FROM events WHERE fb_id = ?", (fb_id,)).fetchone()
    return row is not None


def update_event(event: dict) -> bool:
    # Pure comparison – no DB writes. Caller (main.py) is responsible for saving
    # after a successful API call to prevent desync on failure.
    fb_id = event.get("fbId")

    if _use_mock:
        existing = _mock_db.get(fb_id)
    else:
        row = _get_conn().execute(
            "SELECT start_at, data FROM events WHERE fb_id = ?", (fb_id,)
        ).fetchone()
        existing = {"startAt": row[0], **json.loads(row[1])} if row else None

    if not existing:
        return False

    changed = False

    if existing.get("startAt") != event.get("startAt"):
        print(f"  ⚠ Time change for '{event['name']}': "
              f"{existing.get('startAt')} → {event.get('startAt')} [added to review queue]")
        _add_to_human_review(event, reason="time_changed")
        changed = True

    for field in ["description", "ticketUrl", "imageUrl", "placeName", "category"]:
        if existing.get(field) != event.get(field):
            changed = True
            break

    return changed


def save_event(event: dict):
    fb_id = event.get("fbId")
    if _use_mock:
        _mock_db[fb_id] = event
        return
    _get_conn().execute("""
        INSERT INTO events (fb_id, start_at, data, scraped_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(fb_id) DO UPDATE SET
            start_at = excluded.start_at,
            data = excluded.data,
            scraped_at = excluded.scraped_at
    """, (
        fb_id,
        event.get("startAt"),
        json.dumps(event, ensure_ascii=False),
        event.get("scrappedAt")
    ))
    _get_conn().commit()


def _add_to_human_review(event: dict, reason: str):
    from datetime import datetime, timezone
    if _use_mock:
        _mock_review_queue.append({
            "fbId": event.get("fbId"),
            "name": event.get("name"),
            "reason": reason,
            "aiCategory": event.get("aiCategory"),
        })
        print(f"  → Human review: {event.get('name')} | {reason} | AI: {event.get('aiCategory')}")
        return

    _get_conn().execute("""
        INSERT INTO review_queue (fb_id, name, reason, ai_category, original_category, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event.get("fbId"),
        event.get("name"),
        reason,
        event.get("aiCategory"),
        event.get("category"),
        datetime.now(tz=timezone.utc).isoformat()
    ))
    _get_conn().commit()
    print(f"  → Review queue: {event.get('name')} | {reason} | AI: {event.get('aiCategory')}")
