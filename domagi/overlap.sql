WITH path_overlap AS (
       SELECT path1.id AS path1_id, path1.name AS path1_name, path2.name AS path2_name
       FROM path path1
       INNER JOIN path path2
             ON -- Avoid matching paths to themselves.
                path1.id != path2.id
                -- Check if there is any segment in common between the
                -- two paths.
                AND EXISTS(SELECT segment_id
                           FROM path_segment path_segment1
                           WHERE path_segment1.path_id=path1.id
                           INTERSECT
                           SELECT segment_id
                           FROM path_segment path_segment2
                           WHERE path_segment2.path_id=path2.id)
       WHERE path1.name IN (SELECT UNNEST(?)))
  -- Add path coordinates.
  SELECT path1_name AS "#path", 0 AS start, length AS "end", path2_name AS "path.touched"
  FROM path_overlap
  INNER JOIN path_length ON path_length.path_id=path1_id
