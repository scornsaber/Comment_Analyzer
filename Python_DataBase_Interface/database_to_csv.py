import sqlite3
from pathlib import Path
import csv

# Connect to (or create) a database file
conn = sqlite3.connect("SQLITE_DataBase/comments.db")
cur = conn.cursor()

# Load schema from external file
project_directory = Path.cwd()
file_path = project_directory/"SQLITE_DataBase"/"schema.sql"
with open(file_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

# Path to the output CSV file
output_csv_file = project_directory/"trainingData_csv"/"comments_export.csv"

# Execute the schema (can contain multiple statements)
cur.executescript(schema_sql)

# Export comments to CSV
cur.execute("SELECT id, platform, source_id, author_id, text, published_at, like_count, lang FROM comment")
rows = cur.fetchall()

with open(output_csv_file, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)
    # Write header
    csv_writer.writerow(["id", "platform", "source_id", "author_id", "text",
                         "published_at", "like_count", "lang"])
    # Write data rows
    csv_writer.writerows(rows)

conn.commit()
conn.close()    