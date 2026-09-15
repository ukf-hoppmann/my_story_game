-- Replace the single rolling summary with an append-only chain of immutable
-- summary segments (TASK-032): each completed summary interval produces one
-- new segment that is inserted once and never updated, so the segments in
-- order form the story so far instead of one text being repeatedly
-- overwritten. Same append-only shape as story_turns.
CREATE TABLE story_summary_segments (
    run_id UUID NOT NULL REFERENCES game_runs (run_id) ON DELETE CASCADE,
    from_sequence BIGINT NOT NULL CHECK (from_sequence >= 1),
    through_sequence BIGINT NOT NULL CHECK (through_sequence >= 1),
    text TEXT NOT NULL CHECK (text <> ''),
    based_on_revision BIGINT NOT NULL CHECK (based_on_revision >= 1),
    PRIMARY KEY (run_id, through_sequence),
    FOREIGN KEY (run_id, based_on_revision)
        REFERENCES game_state_revisions (run_id, revision),
    CHECK (from_sequence <= through_sequence)
);

CREATE INDEX story_summary_segments_run_revision_idx
    ON story_summary_segments (run_id, based_on_revision);

-- The old rolling-summary columns are superseded by story_summary_segments.
-- CASCADE drops the unnamed multi-column CHECK constraints that reference
-- them (the all-or-nothing triple and the through-sequence bound).
ALTER TABLE story_state_metadata
    DROP COLUMN summary_through_sequence CASCADE,
    DROP COLUMN summary_text CASCADE,
    DROP COLUMN summary_based_on_revision CASCADE;
