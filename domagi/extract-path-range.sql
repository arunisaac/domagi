-- Select segments in the specified path range.
CREATE TEMPORARY TABLE selected_segment AS
  SELECT segment_id AS id
  FROM path_segment
  INNER JOIN path ON path.id=path_segment.path_id
  WHERE path.name=$1 AND $2<path_segment.end AND path_segment.start<$3;
