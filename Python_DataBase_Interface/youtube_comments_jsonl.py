# Required installations (run these in your terminal before executing the script)
# pip install google-api-python-client langdetect

from googleapiclient.discovery import build
from langdetect import detect, DetectorFactory, LangDetectException
import json

# Ensure consistent language detection results
DetectorFactory.seed = 0

# Your API key and target video ID
API_KEY = 'AIzaSyA5YJrx0hEc0gaxi5u_7rY-ppycSbDdKOc'
VIDEO_ID = 'MG_npaLydKg'  # Replace with any valid YouTube video ID

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Safe wrapper for language detection
def safe_detect(text):
    try:
        return detect(text)
    except LangDetectException:
        return "und"

# Function to retrieve comments
def get_comments(video_id):
    comments = []
    next_page_token = None
    count = 1

    while True:
        response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat='plainText'
        ).execute()

        for item in response['items']:
            snippet = item['snippet']['topLevelComment']['snippet']
            text = snippet.get("textDisplay", "").strip()

            comment = {
                "id": f"yt_{str(count).zfill(3)}",
                "platform": "youtube",
                "video_id": video_id,
                "author_id": snippet.get("authorDisplayName", "unknown"),
                "text": text,
                "published_at": snippet.get("publishedAt", "")[:10],
                "like_count": snippet.get("likeCount", 0),
                "reply_count": item.get("snippet", {}).get("totalReplyCount", 0),
                "lang": safe_detect(text) if text else "und"
            }
            comments.append(comment)
            count += 1

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return comments


def main(VIDEO_ID): 
    comments_data = get_comments(VIDEO_ID)

    with open('youtube_comments.jsonl', 'w', encoding='utf-8') as f:
        for comment in comments_data:
            f.write(json.dumps(comment, ensure_ascii=False) + '\n')

    print(f"Saved {len(comments_data)} comments to youtube_comments.jsonl")


# Run and save to JSONL
if __name__ == "__main__":
    main(VIDEO_ID)