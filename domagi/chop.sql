WITH segment_chops AS (
       SELECT id, name, sequence, range(0, len(sequence), 3) AS starts
       FROM segment),
     segment_chop AS (
       SELECT id, name, sequence, 1 + unnest(starts) AS start, generate_subscripts(starts, 1)-1 AS chop_index
       FROM segment_chops)
    SELECT id, CASE WHEN chop_index=0 THEN name ELSE NULL END, array_slice(sequence, start, start + 3)
    FROM segment_chop;

-- chop index is computed as ceil(a/b) = (a+b-1)//b
-- SELECT id, name, unnest(range(0, len(sequence), 3)) AS starts, unnest(range(0, (len(sequence)+3-1)//3)) AS chop_index
-- FROM segment;
