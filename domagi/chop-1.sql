-- Chop up segments longer than $1 while preserving the graph
-- topology. All segments are renamed. This operation is split across
-- the files chop-*.sql.
CREATE TEMPORARY TABLE segment_chop AS
  WITH segment_chop_start AS (
         -- Chop up segments.
         SELECT id AS parent_id,
                generate_series(1, len(sequence), $1) AS starts,
                unnest(starts) AS start,
                sequence[start:start+$1-1] AS sequence,
                generate_subscripts(starts, 1) AS chop_index
         FROM segment)
    -- Re-number all segment IDs and names with sequential integers.
    -- We start id from 0 and name from 1.
    SELECT row_number() over ()::INTEGER-1 AS id,
           row_number() over ()::VARCHAR AS name,
           sequence,
           parent_id,
           chop_index,
           length(starts) as last_chop
    FROM segment_chop_start;
