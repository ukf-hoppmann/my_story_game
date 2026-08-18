-- The composite primary key on game_run_members is (run_id, issuer, subject),
-- efficient for "is this identity a member of this run" but not for "find
-- all runs for this identity" (GET /api/v1/runs), which needs a full scan
-- without this index.
CREATE INDEX game_run_members_issuer_subject_idx
    ON game_run_members (issuer, subject);
