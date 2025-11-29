import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd
import pytest
import fetch_youtube


class DummyResponse:
    """Fake urllib response object."""
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_extract_video_id():
    assert fetch_youtube.extract_video_id("https://youtu.be/abcdefghijk") == "abcdefghijk"
    assert fetch_youtube.extract_video_id("https://www.youtube.com/watch?v=12345678901") == "12345678901"
    assert fetch_youtube.extract_video_id("shorts/ABCDEFGHIJK") == "ABCDEFGHIJK"
    assert fetch_youtube.extract_video_id("plainid") == "plainid"
    assert fetch_youtube.extract_video_id("") == ""


def test_request_success(monkeypatch):
    payload = {"items": []}

    def fake_urlopen(url):
        return DummyResponse(payload)

    monkeypatch.setattr(fetch_youtube.urllib.request, "urlopen", fake_urlopen)

    result = fetch_youtube._request("http://fakeurl")
    assert result == payload


def test_request_http_error(monkeypatch):
    class FakeHTTPError(Exception):
        def __init__(self):
            self.code = 400
        def read(self):
            return json.dumps({"error": {"message": "Bad Request"}}).encode("utf-8")

    def fake_urlopen(url):
        raise fetch_youtube.HTTPError(url, 400, "Bad Request", None, None)

    # Monkeypatch urllib.request.urlopen to raise HTTPError
    monkeypatch.setattr(fetch_youtube.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError) as e:
        fetch_youtube._request("http://fakeurl")
    assert "YouTube API error" in str(e.value)


def test_fetch_comments(monkeypatch):
    # Fake API response with two comments
    fake_page1 = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorDisplayName": "Tester1",
                            "textDisplay": "Hello",
                            "publishedAt": "2025-01-01T12:00:00Z",
                            "likeCount": 1,
                        }
                    },
                    "totalReplyCount": 0,
                }
            }
        ],
        "nextPageToken": None,
    }

    def fake_request(url):
        return fake_page1

    monkeypatch.setattr(fetch_youtube, "_request", fake_request)

    df = fetch_youtube.fetch_comments("abc123", api_key="FAKEKEY")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["author"] == "Tester1"
    assert row["text"] == "Hello"
    assert row["likes"] == 1
    assert row["replies"] == 0