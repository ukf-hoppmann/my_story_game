-- Global admin switch for world Extraction (llm-integration §6c, provisional).
-- At most one row; no row means tracking is enabled.
CREATE TABLE world_tracking_setting (
    id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    enabled BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL CHECK (updated_by <> '')
);
