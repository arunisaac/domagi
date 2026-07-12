-- Convert internal.path_segment table with position information to
-- this path_segment table with [start, end) information. start and
-- end are zero-based coordinates.
INSERT INTO path_segment
  SELECT path_id,
         segment_id,
         segment_orientation,
         sum(len(sequence)) OVER (PARTITION BY path_id ORDER BY position) - len(sequence) AS start,
         sum(len(sequence)) OVER (PARTITION BY path_id ORDER BY position) AS end
  FROM internal.path_segment
  INNER JOIN segment ON segment.id=path_segment.segment_id
  ORDER BY path_id, start, "end";

-- Drop internal tables and schema.
DROP TABLE internal.path_segment;
DROP SCHEMA internal;
