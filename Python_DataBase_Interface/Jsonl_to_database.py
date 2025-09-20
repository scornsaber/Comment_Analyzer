# Library module: loader.py
# DB init (schema + caps + incremental vacuum) and JSONL loading.

import sqlite3
import json
from pathlib import Path

def init_db(conn: sqlite3.Connection, schema_path: Path, caps_path: Path | None = None) -> None:
    """
    Enables incremental auto-vacuum, applies schema and (optionally) caps SQL.
    Runs a one-time VACUUM if auto_vacuum mode changes.
    """
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema file: {schema_path}")

    (before_mode,) = conn.execute("PRAGMA auto_vacuum;").fetchone()  # 0 NONE, 1 FULL, 2 INCREMENTAL
    conn.execute("PRAGMA auto_vacuum=INCREMENTAL;")

    conn.executescript(schema_path.read_text(encoding="utf-8"))
    if caps_path and caps_path.exists():
        conn.executescript(caps_path.read_text(encoding="utf-8"))

    (after_mode,) = conn.execute("PRAGMA auto_vacuum;").fetchone()
    if before_mode != after_mode:
        conn.execute("VACUUM;")

def load_jsonl_dir(
    conn: sqlite3.Connection,
    jsonl_dir: Path,
    *,
    verbose: bool = False,
    table: str = "comment",
) -> tuple[int, int]:
    """
    Loads all *.jsonl from jsonl_dir into the 'comment' table.
    Returns (inserted, skipped). Reclaims free pages with incremental_vacuum().
    """
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA temp_store=MEMORY;")

    files = sorted(jsonl_dir.glob("*.jsonl"))
    if not files:
        return 0, 0

    sql = f"""
        INSERT OR REPLACE INTO {table}
        (id, platform, video_id, author_id, text, published_at, like_count, reply_count, lang)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    inserted = 0
    skipped = 0

    for path in files:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    cur.execute(sql, (
                        obj["id"],
                        obj["platform"],
                        obj.get("video_id"),
                        obj.get("author_id"),
                        obj["text"],
                        obj.get("published_at"),
                        obj.get("like_count", 0),
                        obj.get("reply_count", 0),
                        obj.get("lang"),
                    ))
                    inserted += 1
                except Exception as e:
                    skipped += 1
                    if verbose:
                        print(f"[SKIP] {path.name}: {e}")

    # reclaim free pages (requires auto_vacuum=INCREMENTAL)
    conn.execute("PRAGMA incremental_vacuum;")
    return inserted, skipped
