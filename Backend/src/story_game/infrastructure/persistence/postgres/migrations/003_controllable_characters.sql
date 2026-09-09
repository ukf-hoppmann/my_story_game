-- Generalize "which figure does this member control" from a single optional
-- entity per membership to zero or more, ordered. Pre-launch schema, no
-- production data: this drops the old column outright rather than adding a
-- backfill/migration path.
ALTER TABLE game_run_members DROP COLUMN player_entity_id;

CREATE TABLE game_run_member_controlled_entities (
    run_id UUID NOT NULL,
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    entity_id UUID NOT NULL,
    PRIMARY KEY (run_id, issuer, subject, entity_id),
    UNIQUE (run_id, issuer, subject, position),
    FOREIGN KEY (run_id, issuer, subject)
        REFERENCES game_run_members (run_id, issuer, subject) ON DELETE CASCADE
);
