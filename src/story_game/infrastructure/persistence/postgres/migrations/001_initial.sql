CREATE TABLE story_runs (
    run_id TEXT PRIMARY KEY,
    player_actor_id TEXT,
    current_revision BIGINT NOT NULL CHECK (current_revision >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE story_state_commits (
    run_id TEXT NOT NULL REFERENCES story_runs (run_id) ON DELETE CASCADE,
    revision BIGINT NOT NULL CHECK (revision >= 1),
    proposal_id TEXT NOT NULL,
    previous_revision BIGINT CHECK (previous_revision IS NULL OR previous_revision >= 1),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, revision),
    UNIQUE (run_id, proposal_id)
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
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
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
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
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
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
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
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
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
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_state_metadata (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    current_scene_id TEXT,
    current_chapter_id TEXT,
    current_sequence BIGINT NOT NULL CHECK (current_sequence >= 0),
    PRIMARY KEY (run_id, revision),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_events (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    event_id TEXT NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence >= 1),
    kind TEXT NOT NULL,
    description TEXT NOT NULL,
    participant_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    visibility_scope TEXT NOT NULL,
    visibility_actor_id TEXT,
    PRIMARY KEY (run_id, revision, event_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_scenes (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    scene_id TEXT NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence >= 1),
    location_id TEXT NOT NULL,
    title TEXT NOT NULL,
    focus TEXT NOT NULL,
    focus_entity_id TEXT,
    PRIMARY KEY (run_id, revision, scene_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_scene_participants (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    scene_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    entity_id TEXT NOT NULL,
    role TEXT NOT NULL,
    visibility_scope TEXT NOT NULL,
    visibility_actor_id TEXT,
    PRIMARY KEY (run_id, revision, scene_id, entity_id),
    UNIQUE (run_id, revision, scene_id, position),
    FOREIGN KEY (run_id, revision, scene_id)
        REFERENCES story_scenes (run_id, revision, scene_id) ON DELETE CASCADE
);

CREATE TABLE story_chapters (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    chapter_id TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK (sequence >= 1),
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    PRIMARY KEY (run_id, revision, chapter_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_threads (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    thread_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
    related_entity_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (run_id, revision, thread_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_goals (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    goal_id TEXT NOT NULL,
    title TEXT NOT NULL,
    owner_id TEXT,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
    related_entity_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (run_id, revision, goal_id),
    UNIQUE (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE TABLE story_summaries (
    run_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    from_sequence BIGINT NOT NULL CHECK (from_sequence >= 1),
    through_sequence BIGINT NOT NULL CHECK (through_sequence >= 1),
    text TEXT NOT NULL,
    based_on_revision BIGINT NOT NULL CHECK (based_on_revision >= 1),
    PRIMARY KEY (run_id, revision, position),
    FOREIGN KEY (run_id, revision)
        REFERENCES story_state_commits (run_id, revision) ON DELETE CASCADE
);

CREATE INDEX story_state_commits_run_revision_idx
    ON story_state_commits (run_id, revision DESC);
