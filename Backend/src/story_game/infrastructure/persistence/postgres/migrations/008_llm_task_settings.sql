-- Per-task model choice, versioned like system_prompts: the first version of
-- each task is seeded from llm.toml; a UI edit or reset deactivates the
-- current row and appends a new one, so the history stays traceable.
-- model_ref is the logical id of a model in the llm.toml catalog. Providers,
-- URLs and secrets stay in the file, never in this table.
CREATE TABLE llm_task_settings (
    version_id UUID PRIMARY KEY,
    task TEXT NOT NULL CHECK (task IN ('story', 'extraction', 'summary', 'scene_image')),
    model_ref TEXT NOT NULL CHECK (btrim(model_ref) <> ''),
    temperature DOUBLE PRECISION CHECK (temperature IS NULL OR (temperature >= 0 AND temperature <= 2)),
    max_output_tokens INTEGER CHECK (max_output_tokens IS NULL OR max_output_tokens > 0),
    source TEXT NOT NULL CHECK (source IN ('toml_seed', 'ui', 'toml_reset')),
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT CHECK (created_by IS NULL OR created_by <> ''),
    is_active BOOLEAN NOT NULL
);

-- Exactly one active version per task.
CREATE UNIQUE INDEX llm_task_settings_one_active_idx
    ON llm_task_settings (task)
    WHERE is_active;

CREATE INDEX llm_task_settings_history_idx
    ON llm_task_settings (task, created_at DESC);
