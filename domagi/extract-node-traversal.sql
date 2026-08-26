CREATE TEMPORARY TABLE selected_segment AS
  WITH RECURSIVE
    cte (id, distance) AS (
      SELECT id, 0 FROM segment WHERE segment.name=?
      UNION ALL
      SELECT DISTINCT to_segment, distance+1 FROM cte
      INNER JOIN (
        -- Eliminate directionality of the link table. We must
        -- traverse both to segments leading out of and to segments
        -- leading into the current segment.
        SELECT from_segment, to_segment FROM link
        UNION
        SELECT to_segment AS from_segment, from_segment AS to_segment FROM link
      )
      ON from_segment=id
      WHERE distance<?
    )
  SELECT DISTINCT id FROM cte;
