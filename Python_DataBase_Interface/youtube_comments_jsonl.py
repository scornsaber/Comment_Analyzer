# Required installations (run these in your terminal before executing the script)
# pip install google-api-python-client langdetect

from googleapiclient.discovery import build
from langdetect import detect, DetectorFactory, LangDetectException
from urllib.parse import urlparse, parse_qs
import json
import re

# Ensure consistent language detection results
DetectorFactory.seed = 0

# Your API key
API_KEY = 'AIzaSyA5YJrx0hEc0gaxi5u_7rY-ppycSbDdKOc'

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Extract video ID from YouTube URL
def extract_video_id(url):
    parsed_url = urlparse(url)

    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]

    if parsed_url.path == '/watch':
        query_params = parse_qs(parsed_url.query)
        return query_params.get('v', [''])[0]

    path_parts = parsed_url.path.split('/')
    if len(path_parts) >= 2:
        return path_parts[-1]

    return ''

# Remove emojis from text
def remove_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002700-\U000027BF"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)

# Safe wrapper for language detection
def safe_detect(text):
    try:
        return detect(text)
    except LangDetectException:
        return "und"

# Retrieve comments from YouTube
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
            raw_text = snippet.get("textDisplay", "").strip()
            clean_text = remove_emojis(raw_text)

            comment = {
                "id": f"yt_{str(count).zfill(3)}",
                "platform": "youtube",
                "video_id": video_id,
                "author_id": snippet.get("authorDisplayName", "unknown"),
                "text": clean_text,
                "published_at": snippet.get("publishedAt", "")[:10],
                "like_count": snippet.get("likeCount", 0),
                "reply_count": item.get("snippet", {}).get("totalReplyCount", 0),
                "lang": safe_detect(clean_text) if clean_text else "und"
            }
            comments.append(comment)
            count += 1

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return comments

# Main execution
if __name__ == "__main__":
    user_url = input("Enter the full YouTube video URL: ")
    VIDEO_ID = extract_video_id(user_url)

    if not VIDEO_ID:
        print("Error: Could not extract video ID from the URL.")
    else:
        comments_data = get_comments(VIDEO_ID)

        with open('youtube_comments.jsonl', 'w', encoding='utf-8') as f:
            for comment in comments_data:
                f.write(json.dumps(comment, ensure_ascii=False) + '\n')

        print(f"Saved {len(comments_data)} comments to youtube_comments.jsonl")