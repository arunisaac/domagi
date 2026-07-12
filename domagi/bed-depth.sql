-- Given a set of BED windows, compute the mean segment depth within
-- each window. The depth of each segment is weighted by the length of
-- the overlap between the segment and the window.
WITH bed_window AS (
       -- Read BED file windows and resolve path names to IDs.
       SELECT row_number() OVER () AS id,
              path.id AS path_id,
              bed.start, bed.end
       FROM read_csv(?,
                     columns={'path_name': 'VARCHAR',
                              'start': 'INTEGER',
                              'end': 'INTEGER'}) AS bed
       INNER JOIN path ON path.name=bed.path_name),
     window_segment AS (
       -- Many-to-many relation associating windows and segments that
       -- intersect, combined with information about the length of
       -- their overlap
       SELECT id AS window_id,
              segment_id,
              (least(bed_window.end, ps.end) - greatest(bed_window.start, ps.start))::INTEGER AS overlap
       FROM bed_window
       INNER JOIN path_segment ps
                  ON bed_window.path_id=ps.path_id
                     AND ps.start<bed_window.end
                     AND ps.end>bed_window.start),
     window_depth AS (
       -- Compute weighted average depth for each window.
       SELECT window_id,
              weighted_avg(depth, overlap) AS mean_depth
       FROM segment_depth
       INNER JOIN window_segment ON window_segment.segment_id=segment_depth.id
       GROUP BY window_id)
    -- Combine window path name and coordinate range with mean depth
    -- for display.
    SELECT path.name, bed_window.start, bed_window.end, mean_depth
    FROM window_depth
    INNER JOIN bed_window ON bed_window.id=window_depth.window_id
    INNER JOIN path ON path.id=bed_window.path_id
    ORDER BY window_id
