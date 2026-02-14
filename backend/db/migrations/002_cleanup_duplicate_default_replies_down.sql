-- Rollback script for 002_cleanup_duplicate_default_replies.sql
-- Re-activates all default reply rules that were disabled

UPDATE autoreply_config
SET is_active = 1
WHERE keyword IS NULL;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = '002_cleanup_duplicate_default_replies';
