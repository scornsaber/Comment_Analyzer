# Testing version   ***not stable

import sqlite3
import json
import gzip
from pathlib import Path

# Connect to (or create) a database file
conn = sqlite3.connect("SQLITE_DataBase/comments.db")
cur = conn.cursor()

# Load schema from external file
project_directory = Path.cwd()
file_path = project_directory/"SQLITE_DataBase"/"schema.sql"
with open(file_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

# Execute the schema (can contain multiple statements)
cur.executescript(schema_sql)


# Example insert
cur.execute("""
INSERT INTO comment (id, platform, source_id, author_id, text, published_at, like_count, lang)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", ("yt_001", "youtube", "abc123", "user_42", "This video is amazing!", "2025-08-28T12:34:00Z", 15, "en"))

conn.commit()
conn.close()
