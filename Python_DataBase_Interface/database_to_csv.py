import sqlite3
from pathlib import Path
import csv

# Connect to (or create) a database file
conn = sqlite3.connect("SQLITE_DataBase/comments.db")
cur = conn.cursor()

project_directory = Path.cwd()
output_csv_file = project_directory/"trainingData_csv"/"comments_export.csv"

# Export comments to CSV
cur.execute("SELECT id, platform, video_id, author_id, text, published_at, like_count, reply_count, lang FROM comment")
rows = cur.fetchall()

with open(output_csv_file, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)
    # Write header
    csv_writer.writerow(["id", "platform", "video_id", "author_id", "text",
                         "published_at", "like_count", "reply_count", "lang"])
    # Write data rows
    csv_writer.writerows(rows)

conn.close()