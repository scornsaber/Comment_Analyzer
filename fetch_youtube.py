import re, json, urllib.parse, urllib.request
import pandas as pd

YOUTUBE_COMMENTS_ENDPOINT = "https://www.googleapis.com/youtube/v3/commentThreads"

def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from a YouTube URL or return raw ID."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url_or_id or "")
    return m.group(1) if m else (url_or_id or "").strip()

def fetch_comments(video_id: str, api_key: str, max_pages: int = 5) -> pd.DataFrame:
    """Fetch comments for a given video_id using YouTube Data API v3."""
    rows, token, pages = [], None, 0
    while True:
        qs = urllib.parse.urlencode({
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "pageToken": token or "",
            "textFormat": "plainText",
            "key": api_key,
        })
        with urllib.request.urlopen(f"{YOUTUBE_COMMENTS_ENDPOINT}?{qs}") as r:
            data = json.loads(r.read().decode("utf-8"))

        for it in data.get("items", []):
            sn = it["snippet"]["topLevelComment"]["snippet"]
            rows.append({
                "author": sn.get("authorDisplayName", "unknown"),
                "text": (sn.get("textDisplay") or "").strip(),
                "published_at": sn.get("publishedAt", ""),
                "likes": sn.get("likeCount", 0),
                "replies": it.get("snippet", {}).get("totalReplyCount", 0),
            })

        token = data.get("nextPageToken")
        pages += 1
        if not token or pages >= max_pages:
            break
    return pd.DataFrame(rows)
