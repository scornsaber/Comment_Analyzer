#!/usr/bin/env python3
# pipeline.py

import os
import sys
import csv
import argparse
import sqlite3
from pathlib import Path

from Python_DataBase_Interface.fetch_comments import fetch_youtube_comments
from Python_DataBase_Interface.Jsonl_to_database import init_db, load_jsonl_dir

ROOT = Path.cwd()
DB_DIR = ROOT / "SQLITE_DataBase"
DB_PATH = DB_DIR / "comments.db"
SCHEMA_PATH = DB_DIR / "schema.sql"
CAPS_PATH = DB_DIR / "enforce_caps.sql"  # optional
JSONL_DIR = ROOT / "trainingData_jsonl"
CSV_DIR = ROOT / "trainingData_csv"
CSV_OUT = CSV_DIR / "comments_export.csv"

def ensure_dirs():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    JSONL_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

def connect_db():
    ensure_dirs()
    return sqlite3.connect(str(DB_PATH))

def cmd_init(_args):
    """Init DB with schema + caps and enable incremental vacuum."""
    ensure_dirs()
    conn = connect_db()
    with conn:
        init_db(conn, SCHEMA_PATH, CAPS_PATH if CAPS_PATH.exists() else None)
    conn.close()
    print(f"Initialized DB at {DB_PATH}")
    if CAPS_PATH.exists():
        print("Applied enforce_caps.sql (indexes + triggers).")

def cmd_fetch_youtube(args):
    """Fetch comments for a video to JSONL."""
    ensure_dirs()
    api_key = os.getenv("YOUTUBE_API_KEY") or args.api_key
    if not api_key:
        print("Provide an API key via --api-key or env var YOUTUBE_API_KEY", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out) if args.out else (JSONL_DIR / f"youtube_{args.video_id}.jsonl")
    path, n = fetch_youtube_comments(
        video_id=args.video_id,
        out_path=out_path,
        api_key=api_key,
        detect_language=True,
    )
    print(f"Saved {n} comments to {path}")

def cmd_load_jsonl(args):
    """Load JSONL files into SQLite."""
    ensure_dirs()
    conn = connect_db()
    with conn:
        inserted, skipped = load_jsonl_dir(conn, JSONL_DIR, verbose=args.verbose)
    conn.close()
    print(f"Loaded {inserted} rows into {DB_PATH} (skipped {skipped})")

def cmd_export_csv(args):
    """Export comments to CSV."""
    ensure_dirs()
    conn = connect_db()
    cur = conn.cursor()
    out = Path(args.out) if args.out else CSV_OUT
    out.parent.mkdir(parents=True, exist_ok=True)

    cur.execute("""
        SELECT id, platform, video_id, author_id, text, published_at, like_count, reply_count, lang
        FROM comment
    """)
    rows = cur.fetchall()
    conn.close()

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id","platform","video_id","author_id","text","published_at","like_count","reply_count","lang"])
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out}")

def main():
    p = argparse.ArgumentParser(description="End-to-end comments pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create/upgrade DB from schema.sql (+ enforce_caps.sql if present)")

    sp = sub.add_parser("fetch-youtube", help="Fetch comments for a YouTube video to JSONL")
    sp.add_argument("--video-id", required=True, help="YouTube video ID")
    sp.add_argument("--api-key", help="YouTube Data API key (or set env YOUTUBE_API_KEY)")
    sp.add_argument("--out", help="Output JSONL path")

    sp = sub.add_parser("load-jsonl", help="Load all JSONL files into SQLite")
    sp.add_argument("-v", "--verbose", action="store_true", help="Log skipped rows")

    sp = sub.add_parser("export-csv", help="Export comments table to CSV")
    sp.add_argument("--out", help="Output CSV path")

    args = p.parse_args()
    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "fetch-youtube":
        cmd_fetch_youtube(args)
    elif args.cmd == "load-jsonl":
        cmd_load_jsonl(args)
    elif args.cmd == "export-csv":
        cmd_export_csv(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()
