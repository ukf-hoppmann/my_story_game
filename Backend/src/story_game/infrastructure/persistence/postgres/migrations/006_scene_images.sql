-- Scene images: a picture of the scene after a given turn, generated on
-- request. Not part of the canonical GameState and never revision-checked:
-- an image only references the run and the turn sequence it was written for.
-- The pixels live in the row (bytea); a failed or pending image has none.
CREATE TABLE scene_images (
    image_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES game_runs (run_id) ON DELETE CASCADE,
    turn_sequence BIGINT NOT NULL CHECK (turn_sequence >= 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'ready', 'failed')),
    model TEXT CHECK (model IS NULL OR model <> ''),
    refine BOOLEAN NOT NULL,
    refine_model TEXT CHECK (refine_model IS NULL OR refine_model <> ''),
    refine_strength DOUBLE PRECISION NOT NULL CHECK (refine_strength > 0),
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    seed BIGINT NOT NULL,
    prompt TEXT CHECK (prompt IS NULL OR prompt <> ''),
    compact_prompt TEXT CHECK (compact_prompt IS NULL OR compact_prompt <> ''),
    error_message TEXT CHECK (error_message IS NULL OR error_message <> ''),
    image BYTEA,
    content_type TEXT CHECK (content_type IS NULL OR content_type <> ''),
    created_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CHECK ((status = 'ready') = (image IS NOT NULL AND content_type IS NOT NULL)),
    CHECK ((status = 'failed') = (error_message IS NOT NULL)),
    CHECK ((status = 'pending') = (completed_at IS NULL))
);

CREATE INDEX scene_images_run_created_idx
    ON scene_images (run_id, created_at DESC);
