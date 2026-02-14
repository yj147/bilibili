-- Cleanup duplicate default reply rules
-- Only keep the first default reply (lowest ID with keyword=NULL)
-- Migration: 002_cleanup_duplicate_default_replies.sql
-- Date: 2026-02-14

-- Create migration tracking table if not exists
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Only run cleanup if this migration has not been recorded yet
UPDATE autoreply_config
SET is_active = 0
WHERE keyword IS NULL
  AND id NOT IN (
    SELECT MIN(id)
    FROM autoreply_config
    WHERE keyword IS NULL
  )
  AND NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '002_cleanup_duplicate_default_replies'
  );

-- Record migration as applied
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('002_cleanup_duplicate_default_replies');
