-- Persist the opening premise and normalized opening prose (previously only
-- held transiently in the run-proposal response and discarded on confirm) so
-- it survives reload and forking into a playthrough, same all-or-nothing
-- pattern as the existing summary columns.
ALTER TABLE story_state_metadata
    ADD COLUMN initialization_prompt TEXT,
    ADD COLUMN initialization_narration TEXT,
    ADD COLUMN initialization_completed_at TIMESTAMPTZ;

ALTER TABLE story_state_metadata
    ADD CONSTRAINT story_state_metadata_initialization_all_or_nothing CHECK (
        (
            initialization_prompt IS NULL
            AND initialization_narration IS NULL
            AND initialization_completed_at IS NULL
        )
        OR (
            initialization_prompt IS NOT NULL
            AND initialization_narration IS NOT NULL
            AND initialization_completed_at IS NOT NULL
        )
    );
