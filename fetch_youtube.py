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
        try:
            detail = e.read().decode("utf-8")
            payload = json.loads(detail)
            msg = payload.get("error", {}).get("message") or payload.get("message") or str(e)
        except Exception:
            msg = str(e)
        raise RuntimeError(f"YouTube API error ({e.code}): {msg}") from None
    except URLError as e:
        raise RuntimeError(f"Network error contacting YouTube: {e.reason}") from None

MAX_COMMENTS = 2000  # hard safety cap

def fetch_comments(video_id: str, api_key: str, max_comments: int = MAX_COMMENTS) -> pd.DataFrame:
    if not api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY (set in Streamlit Secrets or env var).")

    cap = min(max_comments, MAX_COMMENTS)
    rows, token = [], None

    while True:
        qs_params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "textFormat": "plainText",
            "key": api_key,
        }
        if token:
            qs_params["pageToken"] = token

        qs = urllib.parse.urlencode(qs_params)
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

            if len(rows) >= cap:
                return pd.DataFrame(rows)

        token = data.get("nextPageToken")
        if not token:
            break

    return pd.DataFrame(rows)
