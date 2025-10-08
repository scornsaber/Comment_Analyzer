# fetch_youtube.py
import re, json, urllib.parse, urllib.request
import pandas as pd
from urllib.error import HTTPError, URLError

YOUTUBE_COMMENTS_ENDPOINT = "https://www.googleapis.com/youtube/v3/commentThreads"

def extract_video_id(url_or_id: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url_or_id or "")
    return m.group(1) if m else (url_or_id or "").strip()

def _request(url: str) -> dict:
    try:
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        # Try to parse Google error payload for clarity
        try:
            detail = e.read().decode("utf-8")
            payload = json.loads(detail)
            msg = payload.get("error", {}).get("message") or payload.get("message") or str(e)
        except Exception:
            msg = str(e)
        raise RuntimeError(f"YouTube API error ({e.code}): {msg}") from None
    except URLError as e:
        raise RuntimeError(f"Network error contacting YouTube: {e.reason}") from None

MAX_COMMENTS = 2000

def fetch_comments(video_id: str, api_key: str, max_pages: int = 7) -> pd.DataFrame:
    if not api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY (set in Streamlit Secrets or env var).")

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
        data = _request(f"{YOUTUBE_COMMENTS_ENDPOINT}?{qs}")

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
