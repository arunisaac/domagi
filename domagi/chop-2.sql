-- Chop up segments longer than $1 while preserving the graph
-- topology. All segments are renamed. This operation is split across
-- the files chop-*.sql.

-- Write output segment table.
INSERT INTO output_db.segment
SELECT id, name, sequence FROM segment_chop;

CREATE TEMPORARY MACRO invert_orientation(orientation) AS
  CASE WHEN orientation='+' THEN '-'
  ELSE '+'
  END;

WITH link_chop_first AS (
       -- Rewrite existing links to go from the first/last chop of the
       -- "from segment" to the first/last chop of the "to segment"
       -- based on the orientation.
       SELECT from_chop.id AS from_segment,
              from_orientation,
              to_chop.id AS to_segment,
              to_orientation
       FROM link
       INNER JOIN segment_chop AS from_chop ON from_chop.parent_id=link.from_segment
       INNER JOIN segment_chop AS to_chop ON to_chop.parent_id=link.to_segment
       WHERE (from_orientation='+' AND to_orientation='+'
              AND from_chop.chop_index=from_chop.last_chop
              AND to_chop.chop_index=1)
          OR (from_orientation='+' AND to_orientation='-'
              AND from_chop.chop_index=from_chop.last_chop
              AND to_chop.chop_index=to_chop.last_chop)
          OR (from_orientation='-' AND to_orientation='+'
              AND from_chop.chop_index=1
              AND to_chop.chop_index=1)
          OR (from_orientation='-' AND to_orientation='-'
              AND from_chop.chop_index=1
              AND to_chop.chop_index=to_chop.last_chop)),
     link_segment_with_orientation AS (
       -- Derive a list of (segment, orientation) tuples used in the
       -- link table.
       SELECT from_segment AS segment,
              from_orientation AS orientation
       FROM link
       UNION
       SELECT to_segment AS segment,
              to_orientation AS orientation
       FROM link),
     link_chop_internal AS (
       -- Create new links for the other chops—links that were
       -- internal to the original unchopped segment.
       SELECT lag(id) OVER (PARTITION BY parent_id ORDER by chop_index) AS from_segment,
              id AS to_segment,
              parent_id
       FROM segment_chop
       QUALIFY from_segment IS NOT NULL),
     link_chop_internal_with_orientation AS (
       -- Add orientation to the new links.
       SELECT from_segment,
              orientation AS from_orientation,
              to_segment,
              orientation AS to_orientation
       FROM link_chop_internal
       INNER JOIN link_segment_with_orientation
               ON link_segment_with_orientation.segment=link_chop_internal.parent_id
       WHERE orientation='+'
       UNION ALL
       -- Reverse the from/to for negatively oriented segments.
       SELECT to_segment,
              orientation AS from_orientation,
              from_segment,
              orientation AS to_orientation
       FROM link_chop_internal
       INNER JOIN link_segment_with_orientation
               ON link_segment_with_orientation.segment=link_chop_internal.parent_id
       WHERE orientation='-'),
     link_uncanonical AS (
       -- Union all links—new and old—to new table.
       SELECT * FROM link_chop_first
       UNION ALL
       SELECT * FROM link_chop_internal_with_orientation),
     link_canonical AS (
       -- Canonicalize links ensuring that from_segment <= to_segment.
       SELECT *
       FROM link_uncanonical
       WHERE from_segment <= to_segment
       UNION ALL
       SELECT to_segment AS from_segment,
              invert_orientation(to_orientation),
              from_segment AS to_segment,
              invert_orientation(from_orientation)
       FROM link_uncanonical
       WHERE from_segment > to_segment)
  INSERT INTO output_db.link
  -- Write only the distinct links to the output link table.
  SELECT DISTINCT *
  FROM link_canonical;

-- Copy path table.
INSERT INTO output_db.path
SELECT * from path;

-- Split up path segments to reflect the chops.
WITH path_segment_chop AS (
       SELECT path_id,
              id AS segment_id,
              segment_orientation,
              start+$1*(chop_index-1) AS start,
              least(start+$1*chop_index, "end") AS "end",
       FROM path_segment
       INNER JOIN segment_chop ON segment_chop.parent_id=path_segment.segment_id
       WHERE segment_orientation='+'
       UNION ALL
       -- Reverse the order of chops in negatively oriented segments.
       SELECT path_id,
              id AS segment_id,
              segment_orientation,
              start+greatest(0, "end"-start-$1*chop_index) AS start,
              "end"-$1*(chop_index-1) AS "end"
       FROM path_segment
       INNER JOIN segment_chop ON segment_chop.parent_id=path_segment.segment_id
       WHERE segment_orientation='-')
  INSERT INTO output_db.path_segment
  SELECT * FROM path_segment_chop
  -- Re-order similar to post-import.sql for optimal access.
  ORDER BY path_id, start, "end";
