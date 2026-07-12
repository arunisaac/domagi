CREATE schema internal;

-- Internal table that gets inserted into when building the database,
-- but converted to the main.path_segment table and then dropped
-- during post-processing
CREATE TABLE internal.path_segment (
       position INTEGER,
       path_id INTEGER,
       segment_id INTEGER,
       segment_orientation orientation
);
