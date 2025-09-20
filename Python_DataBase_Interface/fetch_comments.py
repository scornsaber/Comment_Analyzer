# Library module: fetch_youtube.py
# Fetch YouTube comments to JSONL. No CLI / __main__ here.

import os
import json
from pathlib import Path

def _imports():
    from googleapiclient.discovery import build
    from langdetect import detect, DetectorFactory, LangDetectException
    DetectorFactory.seed = 0
    return build, detect, LangDetectException

def fetch_youtube_comments(
    video_id: str,
    out_path: Path,
    api_key: str | None = None,
    detect_language: bool = True,
) -> tuple[Path, int]:
    """
    Fetches comments for a video and writes newline-delimited JSON to out_path.
    Returns (out_path, count).

    - video_id: YouTube video ID
    - out_path: file path to write (parent dirs must exist or will be created)
    - api_key: if None, uses env YOUTUBE_API_KEY
    - detect_language: if True, uses langdetect to fill 'lang'
    """
    build, detect, LangDetectException = _imports()

    api_key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("API key required (pass api_key or set env YOUTUBE_API_KEY)")

    youtube = build("youtube", "v3", developerKey=api_key)

    def safe_detect(text: str) -> str:
        if not detect_language:
            return "und"
        try:
            return detect(text) if text else "und"
        except LangDetectException:
            return "und"

    comments = []
    next_page_token = None
    count = 1

    out_path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        resp = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat="plainText",
        ).execute()

        for item in resp.get("items", []):
            sn = item["snippet"]["topLevelComment"]["snippet"]
            text = (sn.get("textDisplay") or "").strip()
            comments.append({
                "id": f"yt_{str(count).zfill(6)}",
                "platform": "youtube",
                "video_id": video_id,
                "author_id": sn.get("authorDisplayName", "unknown"),
                "text": text,
                "published_at": sn.get("publishedAt", "")[:10],
                "like_count": sn.get("likeCount", 0),
                "reply_count": item.get("snippet", {}).get("totalReplyCount", 0),
                "lang": safe_detect(text),
            })
            count += 1

        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break

    with out_path.open("w", encoding="utf-8") as f:
        for c in comments:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return out_path, len(comments)
