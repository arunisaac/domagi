/// domagi --- DuckDB-powered pangenome Swiss Army knife
/// Copyright © 2026 Arun Isaac <arunisaac@systemreboot.net>
///
/// This file is part of domagi.
///
/// domagi is free software: you can redistribute it and/or modify it under the
/// terms of the GNU General Public License as published by the Free Software
/// Foundation, either version 3 of the License, or (at your option) any later
/// version.
///
/// domagi is distributed in the hope that it will be useful, but WITHOUT ANY
/// WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
/// FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
/// details.
///
/// You should have received a copy of the GNU General Public License along with
/// domagi. If not, see <https://www.gnu.org/licenses/>.

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <duckdb.h>

#define NAME str_int_map
#define KEY_TY const char*
#define VAL_TY int
#include <verstable.h>

void die(const char *message)
{
  fprintf(stderr, "%s\n", message);
  exit(EXIT_FAILURE);
}

static int ceildiv (int x, int y)
{
  return (x / y) + (x % y ? 1 : 0);
}

static int hashtable_get (str_int_map *table, const char *key)
{
  // Look up key in hash table and return the corresponding key. The program is
  // aborted if the key is not found. This is ok for our limited purposes since
  // all keys we look up are guaranteed to be present.
  str_int_map_itr itr = vt_get(table, key);
  assert(!vt_is_end(itr));
  return itr.data->val;
}

static uint8_t orientation2int (char c)
{
  return c == '+' ? 0 : 1;
}

static void pass1_handle_s_line (char *line, str_int_map *segment_id_table, duckdb_appender *appender)
{
  static int segment_id = 0;

  // Split S line.
  strsep(&line, "\t");
  char *segment_name = strsep(&line, "\t");
  char *sequence = strsep(&line, "\t\n");

  // Map segment name to ID in table.
  vt_insert(segment_id_table, strdup(segment_name), segment_id);
  // Append to database.
  duckdb_append_int32(*appender, segment_id);
  duckdb_append_varchar(*appender, segment_name);
  duckdb_append_varchar(*appender, sequence);
  duckdb_appender_end_row(*appender);
  // Increment segment ID for next segment.
  segment_id++;
}

static void pass1_handle_p_line (char *line, duckdb_appender *appender)
{
  static int path_id = 0;

  // Split P line.
  strsep(&line, "\t");
  char *path_name = strsep(&line, "\t");

  // Append to database. There are usually relatively few P lines. So, we're
  // content with a simple row-wise appender.
  duckdb_append_int32(*appender, path_id);
  duckdb_append_varchar(*appender, path_name);
  duckdb_appender_end_row(*appender);
  // Increment path ID for next path.
  path_id++;
}

#define LINK_COLUMN_COUNT 4
static void process_l_lines (char **lines, size_t line_count, str_int_map *segment_id_table, duckdb_database *db)
{
  idx_t vector_size = duckdb_vector_size();
  duckdb_logical_type int_type = duckdb_create_logical_type(DUCKDB_TYPE_INTEGER);
  duckdb_logical_type orientation_type = duckdb_create_enum_type((const char *[]){"+", "-"}, 2);
  duckdb_logical_type types[LINK_COLUMN_COUNT]
    = {int_type, orientation_type, int_type, orientation_type};
#pragma omp parallel
  {
    duckdb_connection con;
    if (duckdb_connect(*db, &con) == DuckDBError)
      die("Unable to connect to DuckDB database");
    duckdb_appender appender;
    if (duckdb_appender_create(con, NULL, "link", &appender) == DuckDBError)
      die("Unable to create appender for link table");
    duckdb_data_chunk chunk = duckdb_create_data_chunk(types, LINK_COLUMN_COUNT);
    duckdb_data_chunk_set_size(chunk, vector_size);
    int32_t *from_segment_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 0));
    uint8_t *from_orientation_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 1));
    int32_t *to_segment_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 2));
    uint8_t *to_orientation_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 3));
#pragma omp for
    for (size_t slice_index=0; slice_index<ceildiv(line_count, vector_size); slice_index++) {
      size_t chunk_index, line_index;
      for (chunk_index=0, line_index=slice_index*vector_size;
           (chunk_index<vector_size) && (line_index<line_count);
           chunk_index++, line_index++) {
        char *original_line = lines[line_index];
        // Split L line and write results into data chunk.
        strsep(&lines[line_index], "\t");
        from_segment_data[chunk_index]
          = hashtable_get(segment_id_table, strsep(&lines[line_index], "\t"));
        from_orientation_data[chunk_index]
          = orientation2int(*strsep(&lines[line_index], "\t"));
        to_segment_data[chunk_index]
          = hashtable_get(segment_id_table, strsep(&lines[line_index], "\t"));
        to_orientation_data[chunk_index]
          = orientation2int(*strsep(&lines[line_index], "\t\n"));
        free(original_line);
      }
      // Write chunk to database.
      duckdb_data_chunk_set_size(chunk, chunk_index);
      if (duckdb_append_data_chunk(appender, chunk) == DuckDBError)
        die("Unable to append chunk to link table");
    }
    duckdb_destroy_data_chunk(&chunk);
    duckdb_appender_destroy(&appender);
    duckdb_disconnect(&con);
  }
  duckdb_destroy_logical_type(&int_type);
  duckdb_destroy_logical_type(&orientation_type);
}
#undef LINK_COLUMN_COUNT

#define PATH_SEGMENT_COLUMN_COUNT 4
#define SLICE_SIZE 65536
static void process_p_line (char *line, size_t line_length, str_int_map *segment_id_table, int path_id, duckdb_database *db)
{
  // Split P line.
  strsep(&line, "\t");
  char *path_name = strsep(&line, "\t");
  char *segment_names = strsep(&line, "\t\n");
  // segment_names is likely a very long string, and we want to avoid calling
  // strlen on it. Hence, we compute its length in this roundabout way from the
  // line length.
  size_t segment_names_length = line_length
    // This is the stuff before segment names.
    - strlen("P\t") - strlen(path_name) - strlen("\t")
    // And, this is the stuff after it.
    - (line ? strlen(line) : 0);

  // Split segment_names string into slices.
  // Allocate the slices array to an approximate upper bound; we need not bother
  // with ceil.
  char **slices = malloc((1+segment_names_length/SLICE_SIZE)*sizeof(char*));
  size_t slice_count;
  {
    slices[0] = segment_names;
    int i = 1;
    while (slices[i-1] + SLICE_SIZE < segment_names + segment_names_length) {
      // Start the ith slice SLICE_SIZE bytes away from the beginning of the
      // (i-1)th slice.
      slices[i] = slices[i-1] + SLICE_SIZE;
      // But, extend the (i-1)th slice a bit more so that its end lines up with
      // a comma.
      char *next_comma;
      if ((next_comma = strchr(slices[i], ','))) {
        *next_comma = '\0';
        slices[i] = next_comma + 1;
      }
      i++;
    }
    slice_count = i;
  }

  // Count commas in each slice.
  int *commas = calloc(slice_count, sizeof(int));
#pragma omp parallel for
  for (size_t i=0; i<slice_count; i++) {
    char *slice = slices[i];
    char *comma;
    while ((comma=strchr(slice, ','))) {
      commas[i]++;
      slice = comma + 1;
    }
  }
  // Prefix-sum to get the number of commas in segment_names up to that slice.
  for (size_t i=1; i<slice_count; i++)
    commas[i] += commas[i-1];

  // Split path segments and append them to the database.
  {
    idx_t vector_size = duckdb_vector_size();
    duckdb_logical_type int_type = duckdb_create_logical_type(DUCKDB_TYPE_INTEGER);
    duckdb_logical_type orientation_type = duckdb_create_enum_type((const char *[]){"+", "-"}, 2);
    duckdb_logical_type types[PATH_SEGMENT_COLUMN_COUNT]
      = {int_type, int_type, int_type, orientation_type};
#pragma omp parallel
    {
      duckdb_connection con;
      if (duckdb_connect(*db, &con) == DuckDBError)
        die("Unable to connect to DuckDB database");
      duckdb_appender appender;
      if (duckdb_appender_create(con, "internal", "path_segment", &appender) == DuckDBError)
        die("Unable to create appender for path_segment table");
      duckdb_data_chunk chunk = duckdb_create_data_chunk(types, PATH_SEGMENT_COLUMN_COUNT);
      int32_t *position_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 0));
      int32_t *path_id_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 1));
      int32_t *segment_id_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 2));
      uint8_t *segment_orientation_data = duckdb_vector_get_data(duckdb_data_chunk_get_vector(chunk, 3));
#pragma omp for
      for (size_t i=0; i<slice_count; i++) {
        char orientation;
        int position = i ? commas[i-1] : 0;
        char *comma;
        do {
          size_t chunk_index = 0;
          do {
            char *orientation_ptr;
            if ((comma = strchr(slices[i], ','))) {
              // Comma is found; pick up the orientation character and blot out
              // the comma.
              orientation_ptr = comma - 1;
              *comma = '\0';
            } else
              // Comma is not found; this must be the last segment—the character
              // before the terminating null byte is the orientation character.
              orientation_ptr = strchr(slices[i], '\0') - 1;
            // Copy the orientation character and blot it out from the path
            // segment name.
            orientation = *orientation_ptr;
            *orientation_ptr = '\0';
            // Look up segment ID in hash table.
            int path_segment_id = hashtable_get(segment_id_table, slices[i]);
            // Append to data chunk.
            position_data[chunk_index] = position;
            path_id_data[chunk_index] = path_id;
            segment_id_data[chunk_index] = path_segment_id;
            segment_orientation_data[chunk_index] = orientation2int(orientation);
            // Prepare for the next iteration.
            position++;
            chunk_index++;
            if (comma)
              slices[i] = comma + 1;
          } while (chunk_index<vector_size && comma);
          duckdb_data_chunk_set_size(chunk, chunk_index);
          if (duckdb_append_data_chunk(appender, chunk) == DuckDBError)
            die("Unable to append chunk to path_segment table");
        } while (comma);
      }
      duckdb_destroy_data_chunk(&chunk);
      duckdb_appender_destroy(&appender);
      duckdb_disconnect(&con);
    }
    duckdb_destroy_logical_type(&int_type);
    duckdb_destroy_logical_type(&orientation_type);
  }

  free(commas);
  free(slices);
}
#undef SLICE_SIZE
#undef PATH_SEGMENT_COLUMN_COUNT

int import_gfa (const char *gfa_path, const char *duckdb_path)
{
  str_int_map segment_id_table;
  vt_init(&segment_id_table);

  FILE *gfa_fp = fopen(gfa_path, "r");
  if (!gfa_fp) {
    // TODO: Replace with die.
    fprintf(stderr, "Unable to open GFA: %s\n", gfa_path);
    exit(EXIT_FAILURE);
  }

  duckdb_database db;
  duckdb_connection con;
  if (duckdb_open(duckdb_path, &db) == DuckDBError) {
    // TODO: Replace with die.
    fprintf(stderr, "Unable to open DuckDB database: %s\n", duckdb_path);
    exit(EXIT_FAILURE);
  }
  if (duckdb_connect(db, &con) == DuckDBError)
    die("Unable to connect to DuckDB database");

  char *line = NULL;
  size_t n;
  ssize_t line_length;
  size_t l_line_count = 0;

  // Pass 1
  {
    duckdb_appender segment_appender, path_appender;
    if (duckdb_appender_create(con, NULL, "segment", &segment_appender) == DuckDBError)
      die("Unable to create appender for segment table");
    if (duckdb_appender_create(con, NULL, "path", &path_appender) == DuckDBError)
      die("Unable to create appender for path table");
    while ((getline(&line, &n, gfa_fp)) > 0) {
      switch (line[0]) {
      case 'S':
        pass1_handle_s_line(line, &segment_id_table, &segment_appender);
        break;
      case 'P':
        pass1_handle_p_line(line, &path_appender);
        break;
      case 'L':
        l_line_count++;
        break;
      default:
        break;
      }
    }
    if (duckdb_appender_destroy(&segment_appender) == DuckDBError)
      die("Unable to destroy segment appender");
    if (duckdb_appender_destroy(&path_appender) == DuckDBError)
      die("Unable to destroy path appender");
  }
  rewind(gfa_fp);
  // Pass 2
  {
    char **l_lines = malloc(l_line_count*sizeof(char*));
    size_t l_line_index = 0, path_id = 0;
    while ((line_length = getline(&line, &n, gfa_fp)) > 0) {
      switch (line[0]) {
      case 'L':
        l_lines[l_line_index] = strdup(line);
        l_line_index++;
        break;
      case 'P':
        process_p_line(line, line_length, &segment_id_table, path_id, &db);
        path_id++;
        break;
      default:
        break;
      }
    }
    process_l_lines(l_lines, l_line_count, &segment_id_table, &db);
    free(l_lines);
  }

  free(line);
  fclose(gfa_fp);
  duckdb_disconnect(&con);
  duckdb_close(&db);
  for (str_int_map_itr itr=vt_first(&segment_id_table); !vt_is_end(itr); itr=vt_next(itr))
    free((char*)itr.data->key);
  vt_cleanup(&segment_id_table);

  return 0;
}

int main (int argc, char *argv[])
{
  if (argc != 3) {
    fprintf(stderr, "Usage: %s <gfa_path> <duckdb_path>\n", argv[0]);
    exit(EXIT_FAILURE);
  }
  return import_gfa(argv[1], argv[2]);
}
