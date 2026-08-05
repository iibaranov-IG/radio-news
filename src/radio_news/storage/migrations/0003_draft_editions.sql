CREATE TABLE draft_editions (
    id TEXT PRIMARY KEY,
    selection_id TEXT NOT NULL UNIQUE REFERENCES editorial_selections(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'DRAFT'),
    generator_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE draft_edition_items (
    edition_id TEXT NOT NULL REFERENCES draft_editions(id) ON DELETE CASCADE,
    story_id TEXT NOT NULL REFERENCES stories(id),
    role TEXT NOT NULL CHECK (role IN ('lead', 'body', 'reserve')),
    position INTEGER NOT NULL CHECK (position >= 0),
    generated_baseline TEXT NOT NULL,
    edited_text TEXT NOT NULL,
    source_attribution TEXT NOT NULL,
    estimated_seconds INTEGER NOT NULL CHECK (estimated_seconds >= 0),
    PRIMARY KEY (edition_id, story_id),
    UNIQUE (edition_id, position)
);

CREATE INDEX idx_draft_edition_items_story
    ON draft_edition_items(story_id);

CREATE TRIGGER draft_edition_item_selection_guard
BEFORE INSERT ON draft_edition_items
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1
    FROM draft_editions AS edition
    JOIN editorial_selection_items AS selected
      ON selected.selection_id = edition.selection_id
     AND selected.story_id = NEW.story_id
     AND selected.role = NEW.role
     AND selected.position = NEW.position
    WHERE edition.id = NEW.edition_id
)
BEGIN
    SELECT RAISE(ABORT, 'draft_item_not_in_selection');
END;
