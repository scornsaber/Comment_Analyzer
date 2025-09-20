-- SQLITE_DataBase/enforce_caps.sql
-- Compatible pruning triggers (no CTEs/window functions)

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_comment_video
  ON comment(video_id);

CREATE INDEX IF NOT EXISTS idx_comment_video_pub
  ON comment(video_id, published_at);

-- If old triggers exist, drop them first so we can redefine cleanly
DROP TRIGGER IF EXISTS trg_cap_per_video;
DROP TRIGGER IF EXISTS trg_cap_video_count;

-- Cap each video_id to MOST RECENT 2000 comments (by published_at, tie-break by id)
CREATE TRIGGER trg_cap_per_video
AFTER INSERT ON comment
BEGIN
  DELETE FROM comment
  WHERE video_id = NEW.video_id
    AND id NOT IN (
      SELECT id
      FROM comment
      WHERE video_id = NEW.video_id
      ORDER BY datetime(published_at) DESC, id DESC
      LIMIT 2000
    );
END;

-- Keep only the 5 MOST-RECENTLY ACTIVE videos overall
-- "Activity" = MAX(published_at) within that video.
CREATE TRIGGER trg_cap_video_count
AFTER INSERT ON comment
BEGIN
  DELETE FROM comment
  WHERE video_id IN (
    SELECT video_id FROM (
      SELECT video_id, MAX(datetime(published_at)) AS last_ts
      FROM comment
      GROUP BY video_id
      ORDER BY last_ts DESC
      LIMIT -1 OFFSET 5   -- keep top 5, delete the rest
    )
  );
END;
