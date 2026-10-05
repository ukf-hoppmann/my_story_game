-- System prompts, versioned. The TOML files seed the first version of every
-- entry; a UI edit or a reset never changes a row's text, it deactivates the
-- current row and appends a new one, so the history stays traceable.
-- entry_kind/entry_key mirror the TOML structure (task id, "<category>/<option>",
-- directive id); version_id is the row's own identity.
CREATE TABLE system_prompts (
    version_id UUID PRIMARY KEY,
    package_id TEXT NOT NULL CHECK (package_id <> ''),
    package_version TEXT NOT NULL CHECK (package_version <> ''),
    entry_kind TEXT NOT NULL CHECK (entry_kind IN ('task', 'option', 'directive')),
    entry_key TEXT NOT NULL CHECK (entry_key <> ''),
    entry_text TEXT NOT NULL CHECK (btrim(entry_text) <> ''),
    sort_position INTEGER NOT NULL CHECK (sort_position >= 0),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    task_ids TEXT[] NOT NULL DEFAULT '{}',
    source TEXT NOT NULL CHECK (source IN ('toml_seed', 'ui', 'toml_reset')),
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT CHECK (created_by IS NULL OR created_by <> ''),
    is_active BOOLEAN NOT NULL
);

-- Exactly one active version per entry.
CREATE UNIQUE INDEX system_prompts_one_active_idx
    ON system_prompts (package_id, package_version, entry_kind, entry_key)
    WHERE is_active;

CREATE INDEX system_prompts_history_idx
    ON system_prompts (package_id, package_version, entry_kind, entry_key, created_at DESC);
