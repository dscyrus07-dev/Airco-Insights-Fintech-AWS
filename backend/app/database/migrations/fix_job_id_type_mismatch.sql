-- Migration: Fix job_id type mismatch between user_file_records and statement_metadata
-- Issue: user_file_records.job_id is VARCHAR, statement_metadata.job_id is UUID
-- Error: operator does not exist: character varying = uuid

-- Step 1: Drop the existing foreign key constraint (it references processing_jobs.id anyway, not user_file_records)
ALTER TABLE statement_metadata DROP CONSTRAINT IF EXISTS statement_metadata_job_id_fkey;

-- Step 2: Drop the unique index on job_id
DROP INDEX IF EXISTS ix_statement_metadata_job_id;

-- Step 3: Alter the column type from UUID to VARCHAR(64) to match user_file_records.job_id
ALTER TABLE statement_metadata ALTER COLUMN job_id TYPE VARCHAR(64);

-- Step 4: Recreate the unique index
CREATE UNIQUE INDEX ix_statement_metadata_job_id ON statement_metadata (job_id);

-- Step 5: Add a comment explaining the relationship
COMMENT ON COLUMN statement_metadata.job_id IS 'String job_id matching user_file_records.job_id (not a FK to allow loose coupling)';
