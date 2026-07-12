-- Compute the mean segment depth for all paths, or a subset thereof.
-- The depth of each segment is weighted by its sequence length.
WITH path_depth AS (
       -- Compute weighted average segment depth of each path.
       SELECT path_id, weighted_avg(depth, len(sequence)) AS mean_depth
       FROM segment_depth
       INNER JOIN segment ON segment.id=segment_depth.id
       INNER JOIN path_segment ON path_segment.segment_id=segment_depth.id
       INNER JOIN path ON path.id=path_segment.path_id
       -- subset paths
       WHERE ($1 IS NULL) OR (path.name IN (SELECT UNNEST($1)))
       GROUP BY path_id),
     path_length AS (
       -- Compute length of each path.
       SELECT path_id, sum(len(sequence)) AS length
       FROM path_segment
       INNER JOIN segment ON segment_id=segment.id
       INNER JOIN path ON path.id=path_segment.path_id
       -- subset paths (same filter as above)
       WHERE (($1 IS NULL) OR (path.name IN (SELECT UNNEST($1))))
       GROUP BY path_id)
    -- Combine path name, length and mean depth for display.
    SELECT name, length, mean_depth
    FROM path_depth
    INNER JOIN path_length ON path_depth.path_id=path_length.path_id
    INNER JOIN path ON path.id=path_length.path_id
