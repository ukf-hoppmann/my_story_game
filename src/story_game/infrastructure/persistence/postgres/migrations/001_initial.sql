CREATE TABLE game_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    current_revision BIGINT NOT NULL CHECK (current_revision >= 1),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CHECK (updated_at >= created_at)
);

CREATE TABLE game_run_members (
    run_id TEXT NOT NULL REFERENCES game_runs (run_id) ON DELETE CASCADE,
    issuer TEXT NOT NULL CHECK (issuer <> ''),
    subject TEXT NOT NULL CHECK (subject <> ''),
    game_role TEXT NOT NULL CHECK (game_role IN ('owner', 'player')),
    player_entity_id TEXT,
    PRIMARY KEY (run_id, issuer, subject)
);

CREATE TABLE game_state_revisions (
    run_id TEXT NOT NULL REFERENCES game_runs (run_id) ON DELETE CASCADE,
    revision BIGINT NOT NULL CHECK (revision >= 1),
    previous_revision BIGINT CHECK (previous_revision IS NULL OR previous_revision >= 1),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, revision),
    CHECK (
        (revision = 1 AND previous_revision IS NULL)
        OR previous_revision = revision - 1
    )
);

CREATE TABLE game_state_configurations (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    language TEXT NOT NULL CHECK (language <> ''),
    narration_style_id TEXT NOT NULL CHECK (narration_style_id <> ''),
    perspective_id TEXT NOT NULL CHECK (perspective_id <> ''),
    control_mode_id TEXT NOT NULL CHECK (control_mode_id <> ''),
    narrative_boundaries JSONB NOT NULL DEFAULT '[]'::jsonb,
    story_model_id TEXT NOT NULL CHECK (story_model_id <> ''),
    extraction_model_id TEXT NOT NULL CHECK (extraction_model_id <> ''),
    summary_model_id TEXT NOT NULL CHECK (summary_model_id <> ''),
    prompt_package_id TEXT NOT NULL CHECK (prompt_package_id <> ''),
    prompt_package_version TEXT NOT NULL CHECK (prompt_package_version <> ''),
    PRIMARY KEY (run_id, revision),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE world_entities (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    entity_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    actor_role TEXT,
    conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (run_id, revision, entity_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE world_links (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    link_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    visibility_scope TEXT NOT NULL,
    visibility_actor_id TEXT,
    quantity INTEGER CHECK (quantity IS NULL OR quantity >= 1),
    description TEXT NOT NULL,
    PRIMARY KEY (run_id, revision, link_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE world_facts (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    fact_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    subject_id TEXT,
    evidence_source TEXT NOT NULL,
    evidence_reference TEXT,
    evidence_excerpt TEXT,
    visibility_scope TEXT NOT NULL,
    visibility_actor_id TEXT,
    PRIMARY KEY (run_id, revision, fact_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE world_knowledge (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    actor_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    learned_at BIGINT NOT NULL CHECK (learned_at >= 1),
    forgotten_at BIGINT CHECK (forgotten_at IS NULL OR forgotten_at >= 1),
    PRIMARY KEY (run_id, revision, actor_id, fact_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE world_rules (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    rule_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    evidence_source TEXT NOT NULL,
    evidence_reference TEXT,
    evidence_excerpt TEXT,
    visibility_scope TEXT NOT NULL,
    visibility_actor_id TEXT,
    PRIMARY KEY (run_id, revision, rule_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE world_goals (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    goal_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('main', 'side')),
    title TEXT NOT NULL CHECK (title <> ''),
    description TEXT NOT NULL CHECK (description <> ''),
    status TEXT NOT NULL CHECK (status IN ('open', 'completed', 'failed')),
    related_entity_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (run_id, revision, goal_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_state_metadata (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    current_turn_sequence BIGINT NOT NULL CHECK (current_turn_sequence >= 0),
    summary_through_sequence BIGINT CHECK (summary_through_sequence >= 1),
    summary_text TEXT,
    summary_based_on_revision BIGINT CHECK (summary_based_on_revision >= 1),
    PRIMARY KEY (run_id, revision),
    FOREIGN KEY (run_id, revision)
        REFERENCES game_state_revisions (run_id, revision) ON DELETE CASCADE,
    CHECK (
        (summary_through_sequence IS NULL AND summary_text IS NULL AND summary_based_on_revision IS NULL)
        OR (summary_through_sequence IS NOT NULL AND summary_text IS NOT NULL AND summary_based_on_revision IS NOT NULL)
    ),
    CHECK (
        summary_through_sequence IS NULL
        OR summary_through_sequence <= current_turn_sequence
    )
);

CREATE TABLE story_turns (
    run_id TEXT NOT NULL REFERENCES game_runs (run_id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence >= 1),
    player_input TEXT NOT NULL CHECK (player_input <> ''),
    narration TEXT NOT NULL CHECK (narration <> ''),
    based_on_revision BIGINT NOT NULL CHECK (based_on_revision >= 1),
    resulting_revision BIGINT NOT NULL CHECK (resulting_revision >= 2),
    completed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (run_id, turn_id),
    UNIQUE (run_id, sequence),
    UNIQUE (run_id, resulting_revision),
    FOREIGN KEY (run_id, based_on_revision)
        REFERENCES game_state_revisions (run_id, revision),
    FOREIGN KEY (run_id, resulting_revision)
        REFERENCES game_state_revisions (run_id, revision),
    CHECK (resulting_revision = based_on_revision + 1)
);

CREATE INDEX game_state_revisions_run_revision_idx
    ON game_state_revisions (run_id, revision DESC);

CREATE INDEX story_turns_run_resulting_revision_idx
    ON story_turns (run_id, resulting_revision);
