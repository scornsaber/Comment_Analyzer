-- SQLITE_DataBase/enforce_caps.sql
-- Enforce caps + performance indexes
-- Requires SQLite with window functions (3.25+). Most modern builds qualify.

-- Indexes (speed up pruning + queries)
CREATE INDEX IF NOT EXISTS idx_comment_video
  ON comment(video_id);

CREATE INDEX IF NOT EXISTS idx_comment_video_pub
  ON comment(video_id, published_at);

-- Cap each video_id to the most recent 2000 comments (by published_at, tie-break id)
CREATE TRIGGER IF NOT EXISTS trg_cap_per_video
AFTER INSERT ON comment
BEGIN
  WITH ranked AS (
    SELECT id,
           ROW_NUMBER() OVER (
             PARTITION BY video_id
             ORDER BY datetime(published_at) DESC, id DESC
           ) AS rn
    FROM comment
    WHERE video_id = NEW.video_id
  )
  DELETE FROM comment
  WHERE id IN (SELECT id FROM ranked WHERE rn > 2000); -- This number may can be adjusted
END;

-- Keep only 5 video_ids total, drop least-recently-active ones
-- "Activity" = latest published_at among that video's comments.
CREATE TRIGGER IF NOT EXISTS trg_cap_video_count
AFTER INSERT ON comment
BEGIN
  WITH last_activity AS (
    SELECT video_id, MAX(datetime(published_at)) AS last_ts
    FROM comment
    GROUP BY video_id
  ),
  to_drop AS (
    SELECT video_id
    FROM last_activity
    ORDER BY last_ts DESC
    LIMIT -1 OFFSET 5    -- keep top 5, mark the rest to drop
  )
  DELETE FROM comment
  WHERE video_id IN (SELECT video_id FROM to_drop);
END;
