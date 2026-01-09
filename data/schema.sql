-- Sparse Wiki Grounding Database Schema
-- This is the schema used by entities_demo.db and entities_full.db

CREATE TABLE entities (
    id TEXT PRIMARY KEY,           -- Wikidata Q-number (e.g., "Q90")
    wikipedia_title TEXT UNIQUE,   -- Canonical Wikipedia title
    label TEXT NOT NULL,           -- Human-readable name
    description TEXT,              -- Short description
    vital_level INTEGER,           -- 1-5 from Wikipedia Vital Articles
    pagerank REAL                  -- Importance score
);

CREATE TABLE dimension_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(id),
    dimension TEXT NOT NULL,       -- SPATIAL, TEMPORAL, TAXONOMIC, SCALE, DOMAIN
    path_sign INTEGER NOT NULL,    -- +1 (specific) or -1 (abstract) or 0
    path_depth INTEGER NOT NULL,   -- Distance from zero state
    path_nodes TEXT NOT NULL,      -- JSON array of path
    zero_state TEXT NOT NULL       -- Zero state for dimension
);

CREATE TABLE epa_values (
    entity_id TEXT PRIMARY KEY REFERENCES entities(id),
    evaluation INTEGER NOT NULL DEFAULT 0,  -- -1, 0, +1
    potency INTEGER NOT NULL DEFAULT 0,     -- -1, 0, +1
    activity INTEGER NOT NULL DEFAULT 0,    -- -1, 0, +1
    confidence REAL DEFAULT 1.0
);

CREATE TABLE properties (
    entity_id TEXT NOT NULL REFERENCES entities(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (entity_id, key)
);

CREATE TABLE entity_links (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    UNIQUE(source_id, target_id, relation)
);

-- Indexes for performance
CREATE INDEX idx_entities_label ON entities(label);
CREATE INDEX idx_entities_label_lower ON entities(LOWER(label));
CREATE INDEX idx_dim_pos_entity ON dimension_positions(entity_id);
CREATE INDEX idx_links_source ON entity_links(source_id);
CREATE INDEX idx_links_target ON entity_links(target_id);
