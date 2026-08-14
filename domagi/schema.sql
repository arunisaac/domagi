CREATE TYPE orientation as ENUM ('+', '-');

CREATE TABLE segment (
       id INTEGER,
       name VARCHAR,
       sequence VARCHAR
);

CREATE TABLE link (
       from_segment INTEGER,
       from_orientation orientation,
       to_segment INTEGER,
       to_orientation orientation
);

CREATE TABLE path (
       id INTEGER,
       name VARCHAR
);

CREATE TABLE path_segment (
       path_id INTEGER,
       segment_id INTEGER,
       segment_orientation orientation,
       -- Zero-based inclusive start coordinate of segment on the path
       start INTEGER,
       -- Zero-based exclusive end coordinate of segment on the path
       "end" INTEGER,
);

-- One-to-one relation mapping path IDs to their length
CREATE VIEW path_length AS
  SELECT ANY_VALUE(path_id) AS path_id, sum(len(sequence))::INTEGER AS length
  FROM path_segment
  INNER JOIN segment ON segment.id=path_segment.segment_id
  GROUP BY path_id;

-- One-to-one relation mapping segment IDs to their depth
CREATE VIEW segment_depth AS
  WITH segment_depth_nonzero_depths_only AS (
       SELECT segment_id AS id,
              count()::INTEGER AS depth,
              count(DISTINCT path_id)::INTEGER AS unique_depth
       FROM path_segment
       GROUP BY segment_id)
    -- Segments that were not crossed by any paths will have a NULL
    -- depth; we set their depth to 0.
    SELECT segment.id,
           ifnull(depth, 0) AS depth,
           ifnull(unique_depth, 0) AS unique_depth
    FROM segment
    LEFT JOIN segment_depth_nonzero_depths_only nzdepth ON segment.id=nzdepth.id;
