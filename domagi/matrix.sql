WITH segment_indices AS (
       SELECT id, dense_rank() OVER (ORDER BY id) AS index
       FROM segment),
     matrix AS (
       SELECT source.index AS source, destination.index AS destination
       FROM link
       INNER JOIN segment_indices source ON link.from_segment=source.id
       INNER JOIN segment_indices destination ON link.to_segment=destination.id)
    SELECT source, destination, 1
    FROM matrix
    UNION ALL
    SELECT destination, source, 1
    FROM matrix
  
