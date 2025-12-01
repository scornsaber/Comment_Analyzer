-- Version 0.01 will likely change

CREATE TABLE comment (
    id TEXT PRIMARY KEY,        -- "yt_001", "tw_001", etc.
    platform TEXT NOT NULL,     -- 'youtube', 'twitter', 'reddit'
    video_id TEXT,             -- video_id / tweet_id / thread_id
    author_id TEXT,
    text TEXT NOT NULL,
    published_at TEXT,          -- ISO 8601 timestamp
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    lang TEXT
);