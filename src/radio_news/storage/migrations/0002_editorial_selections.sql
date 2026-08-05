CREATE TABLE editorial_selections (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'DRAFT'),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE editorial_selection_items (
    selection_id TEXT NOT NULL REFERENCES editorial_selections(id) ON DELETE CASCADE,
    story_id TEXT NOT NULL REFERENCES stories(id),
    role TEXT NOT NULL CHECK (role IN ('lead', 'body', 'reserve')),
    position INTEGER NOT NULL CHECK (position >= 0),
    PRIMARY KEY (selection_id, story_id),
    UNIQUE (selection_id, position)
);

CREATE INDEX idx_editorial_selection_items_story
    ON editorial_selection_items(story_id);
