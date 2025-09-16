# Testing version   ***not stable

import sqlite3
import json
from pathlib import Path

# Connect to (or create) a database file
conn = sqlite3.connect("SQLITE_DataBase/comments.db")
cur = conn.cursor()



# Load schema from external file
project_directory = Path.cwd()
file_path = project_directory/"SQLITE_DataBase"/"schema.sql"
with open(file_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

# Path to the comments JSONL directory
comments_dir = project_directory/"trainingData_jsonl"

# Execute the schema (can contain multiple statements)
cur.executescript(schema_sql)


# Insert comments from all .jsonl files in the directory
for comments_file in comments_dir.glob("*.jsonl"):
    with open(comments_file, "r", encoding="utf-8") as f:
        for line in f:
            comment = json.loads(line)
            cur.execute("""
                INSERT INTO comment (id, platform, video_id, author_id, text, published_at, like_count, reply_count, lang)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment["id"],
                comment["platform"],
                comment["video_id"],
                comment["author_id"],
                comment["text"],
                comment["published_at"],
                comment["like_count"],
                comment["reply_count"],
                comment["lang"]
            ))

conn.commit()
conn.close()
