### domagi --- DuckDB-powered pangenome Swiss Army knife
### Copyright © 2026 Arun Isaac <arunisaac@systemreboot.net>
###
### This file is part of domagi.
###
### domagi is free software: you can redistribute it and/or modify it under the
### terms of the GNU General Public License as published by the Free Software
### Foundation, either version 3 of the License, or (at your option) any later
### version.
###
### domagi is distributed in the hope that it will be useful, but WITHOUT ANY
### WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
### FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
### details.
###
### You should have received a copy of the GNU General Public License along with
### domagi. If not, see <https://www.gnu.org/licenses/>.

from contextlib import contextmanager
import importlib.resources
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import click
import duckdb

threads_option = click.option("-t", "--threads",
                              type=click.INT,
                              help="number of threads (default: number of CPUs)")
# The -P, --progress flags are no-ops in domagi. But, we add them to remain
# compatible with odgi.
progress_option = click.option("-P", "--progress", is_flag=True, hidden=True)

def common_options(func):
    return threads_option(progress_option(func))

class DuckDBParamType(click.ParamType):
    name = "DB"
    def __init__(self, read_only=True):
        self.read_only = read_only
    def convert(self, value, param, ctx):
        # The click manual recommends checking for already valid
        # values and passing them through.
        if isinstance(value, duckdb.DuckDBPyConnection):
            return value
        try:
            return ctx.with_resource(duckdb.connect(value, self.read_only))
        except duckdb.Error as err:
            self.fail(str(err), param, ctx)

def set_duckdb_threads(con, threads):
    if threads:
        con.execute(f"SET threads TO {threads}")

def assert_paths_exist(con, paths):
    non_existent_paths = [path for path, in con.execute("""
    SELECT UNNEST(?)
    EXCEPT
    SELECT name FROM path
    """,
    [paths]).fetchall()]
    if non_existent_paths:
        sys.exit(f"Paths {non_existent_paths} not found")

@contextmanager
def connect_duckdb(path, threads):
    with duckdb.connect(path) as con:
        set_duckdb_threads(con, threads)
        yield con

def read_sql(filename):
    # TODO: Move sql queries into their own directory and update this
    # function once we move to python 3.13+. Only python 3.13+
    # supports multiple path names in read_text.
    return importlib.resources.read_text(__package__, filename)

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass

@main.command(short_help="Convert GFA pangenome file to domagi DuckDB database")
@click.option("-g", "--gfa", "gfa",
              metavar="FILE",
              required=True,
              help="GFAv1 pangenome")
@click.option("-o", "--out", "db",
              type=click.Path(),
              required=True,
              help="output pangenome duckdb database")
@common_options
def build(gfa, db, threads, progress):
    with connect_duckdb(db, threads) as con:
        con.execute(read_sql("schema.sql"))
    with connect_duckdb(db, threads) as con:
        con.execute(read_sql("pre-import.sql"))
    subprocess.run([shutil.which("domagi_importgfa"), gfa, db],
                   env={"OMP_NUM_THREADS": str(threads)} if threads else None)
    with connect_duckdb(db, threads) as con:
        con.execute(read_sql("post-import.sql"))

@main.command(short_help="Divide segments into smaller pieces")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-o", "--out", "outfile",
              type=click.Path(),
              required=True,
              help="path to output pangenome duckdb database")
@click.option("-c", "--chop-to",
              type=click.INT,
              metavar="N",
              required=True,
              help="divide segments longer than N")
@common_options
def chop(con, outfile, chop_to, threads, progress):
    set_duckdb_threads(con, threads)
    with connect_duckdb(outfile, threads) as out_con:
        out_con.execute(read_sql("schema.sql"))
    con.execute(f"ATTACH '{outfile}' AS output_db (READ_WRITE)")
    # At the moment, DuckDB only supports prepared parameters in the last
    # statement. Hence, we have to split up the statements into separate execute
    # calls.
    con.execute(read_sql("chop-1.sql"), [chop_to])
    con.execute(read_sql("chop-2.sql"), [chop_to])
    con.execute("""
    DROP TABLE segment_chop;
    DETACH output_db;
    """)

@main.command(short_help="Crush runs of Ns")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-o", "--out", "outfile",
              type=click.Path(),
              required=True,
              help="path to output pangenome duckdb database")
@common_options
def crush(con, outfile, threads, progress):
    set_duckdb_threads(con, threads)
    with connect_duckdb(outfile, threads) as out_con:
        out_con.execute(read_sql("schema.sql"))
    con.execute(f"""
    ATTACH '{outfile}' AS output_db (READ_WRITE);
    
    INSERT INTO output_db.segment
      SELECT segment.id, name, regexp_replace(sequence, 'N+', 'N', 'g') AS sequence
      FROM segment;

    INSERT INTO output_db.link
      SELECT * FROM link;

    INSERT INTO output_db.path
      SELECT * FROM path;

    INSERT INTO output_db.path_segment
      SELECT * FROM path_segment
      ORDER BY path_id, start, "end"
    """)

@main.command(short_help="Compute depth of graph nodes")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-d", "--graph-depth-table",
              is_flag=True,
              help="print depth and unique depth of every node")
@click.option("-r", "--path", "paths",
              # We deviate a little from odgi and allow -r to be
              # specified several times.
              multiple=True,
              help="only compute the depth of the given path")
@click.option("-b", "--bed-input",
              help="BED file of windows to compute depth over")
@common_options
def depth(con, graph_depth_table, paths, bed_input, threads, progress):
    set_duckdb_threads(con, threads)
    assert_paths_exist(con, paths)
    # With the -d flag, print the depth and unique depth of every
    # node.
    if graph_depth_table:
        print("\t".join(["#node.id", "depth", "depth.uniq"]))
        for segment_name, depth, unique_depth in con.execute("""
        SELECT name, depth, unique_depth
        FROM segment_depth
        INNER JOIN segment ON segment.id=segment_depth.id
        """).fetchall():
            print("\t".join([segment_name, str(depth), str(unique_depth)]))
    elif bed_input:
        print("\t".join(["#path", "start", "end", "mean.depth"]))
        for path_name, start, end, mean_depth in con.execute(
                read_sql("bed-depth.sql"),
                [bed_input]).fetchall():
            print("\t".join([path_name, str(start), str(end), str(mean_depth)]))
    # Else, print the mean node depth of each path.
    else:
        print("\t".join(["#path", "start", "end", "mean.depth"]))
        for path_name, end, mean_depth in con.execute(
                read_sql("path-depth.sql"),
                [paths if paths else None]).fetchall():
            # The start is always 0.
            print("\t".join([path_name, str(0), str(end), str(mean_depth)]))

@main.command(short_help="Extract subgraphs")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="input pangenome duckdb database")
@click.option("-o", "--out", "outfile",
              type=click.Path(),
              required=True,
              help="path to output pangenome duckdb database")
@click.option("-n", "--node", "segment_name",
              type=click.STRING,
              help="segment name from which to begin the traversal")
@click.option("-r", "--path-range", "path_range",
              type=click.STRING,
              help="path range specifying segments from which to begin the traversal")
@click.option("-c", "--context-steps", "steps",
              type=click.INT,
              # TODO: Add default=0
              required=True,
              help="number of traversal steps")
@common_options
def extract(con, outfile, segment_name, path_range, steps, threads, progress):
    set_duckdb_threads(con, threads)
    with connect_duckdb(outfile, threads) as out_con:
        out_con.execute(read_sql("schema.sql"))
    if segment_name:
        con.execute("""
        CREATE TEMPORARY TABLE initial_segment AS
          SELECT id FROM segment WHERE segment.name=?
        """,
                    [segment_name])
    elif path_range:
        # TODO: We're assuming the interval is [start, end) rather
        # than [start, end]. But check what odgi does.
        con.execute("""
        CREATE TEMPORARY TABLE initial_segment AS
          SELECT segment_id AS id
          FROM path_segment
          INNER JOIN path ON path.id=path_segment.path_id
          WHERE path.name=? AND start>=? AND start<?;
        """,
        # TODO: Convert extracted strings to integers.
        re.match(r"^([^:]*):(\d+)-(\d+)", path_range).groups())
    else:
        raise ValueError("Neither --node and --path-range specified")
    con.execute("""
    CREATE TEMPORARY TABLE reachable_segment AS
      WITH RECURSIVE cte (id, distance) AS (
          SELECT id, 0 FROM initial_segment
        UNION ALL
          SELECT DISTINCT to_segment, distance+1 FROM cte
          INNER JOIN (
            -- Eliminate directionality of the link table. We must traverse both
            -- to segments leading out of and to segments leading into the
            -- current segment.
            SELECT from_segment, to_segment FROM link
            UNION
            SELECT to_segment AS from_segment, from_segment AS to_segment FROM link
          )
          ON from_segment=id
          WHERE distance<?
      )
      SELECT DISTINCT id FROM cte;
    """,
                   [steps])
    con.execute(f"""
    ATTACH '{outfile}' AS subset_db (READ_WRITE);
    
    INSERT INTO subset_db.segment
    SELECT segment.id, name, sequence FROM reachable_segment
    INNER JOIN segment ON segment.id=reachable_segment.id;

    INSERT INTO subset_db.link
    SELECT from_segment, from_orientation, to_segment, to_orientation
    FROM reachable_segment
    INNER JOIN link ON from_segment=reachable_segment.id;
    
    INSERT INTO subset_db.path_segment
    SELECT path_id, segment_id, segment_orientation, start, "end"
    FROM reachable_segment
    INNER JOIN path_segment ON path_segment.segment_id=reachable_segment.id;
    
    INSERT INTO subset_db.path
    SELECT id, ANY_VALUE(name)
    FROM subset_db.path_segment
    INNER JOIN path ON subset_db.path_segment.path_id=path.id
    GROUP BY id;

    DROP TABLE reachable_segment;
    DROP TABLE initial_segment;
    """)

@main.command(short_help="Write graph in sparse matrix format")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@common_options
def matrix(con, threads, progress):
    set_duckdb_threads(con, threads)
    segment_count, = con.execute("SELECT COUNT() FROM segment").fetchone()
    df = con.execute(read_sql("matrix.sql")).fetchdf()
    print(segment_count, segment_count, df.shape[0])
    df.to_csv(sys.stdout, sep=" ", header=False, index=False)

@main.command(short_help="Find paths touched by given input paths")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-r", "--path", "paths",
              # We deviate a little from odgi and allow -r to be specified
              # several times.
              multiple=True,
              metavar="PATH",
              help="find paths touched by PATH")
@click.option("-R", "--paths", "paths_file",
              type=click.File(),
              metavar="FILE",
              help="find paths touched by paths listed in FILE")
@common_options
def overlap(con, paths, paths_file, threads, progress):
    set_duckdb_threads(con, threads)
    if paths_file:
        paths = [line.rstrip() for line in paths_file.readlines()]
    assert_paths_exist(con, paths)
    (con.execute(read_sql("overlap.sql"), [paths])
     .fetchdf()
     .to_csv(sys.stdout, sep="\t", index=False))

@main.command(short_help="Interrogate paths")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-L", "--list-paths",
              is_flag=True,
              help="print path names")
@click.option("-f", "--fasta", "fasta",
              is_flag=True,
              help="print paths in FASTA format")
@common_options
def paths(con, list_paths, fasta, threads, progress):
    set_duckdb_threads(con, threads)
    if list_paths:
        for name, in con.execute("SELECT name FROM path").fetchall():
            print(name)
    elif fasta:
        # We take care to reverse complement soft masked lower case nucleotides
        # as well.
        for name, sequence in con.execute("""
        SELECT ANY_VALUE(path.name),
               string_agg(CASE WHEN segment_orientation='+' THEN sequence
                          ELSE reverse(translate(sequence, 'AGCTagct', 'TCGAtcga'))
                          END,
                          '' ORDER BY start)
        FROM path_segment
        INNER JOIN segment ON segment.id = path_segment.segment_id
        INNER JOIN path ON path.id = path_segment.path_id
        GROUP BY path_id
        """).fetchall():
            print(f">{name}")
            print(sequence)

@main.command(short_help="Compute graph statistics")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
# The --summarize flag seems to be a no-op in odgi.
@click.option("-S", "--summarize",
              is_flag=True)
@common_options
def stats(con, summarize, threads, progress):
    set_duckdb_threads(con, threads)
    print("\t".join(["#length", "nodes", "edges", "paths", "steps"]))
    length, = con.execute("SELECT sum(len(sequence)) FROM segment").fetchone()
    nodes, = con.execute("SELECT COUNT() FROM segment").fetchone()
    edges, = con.execute("SELECT COUNT() FROM link").fetchone()
    paths, = con.execute("SELECT COUNT() FROM path").fetchone()
    steps, = con.execute("SELECT COUNT() FROM path_segment").fetchone()
    print("\t".join([str(length), str(nodes), str(edges),
                     str(paths), str(steps)]))

@main.command(short_help="Convert domagi DuckDB database pangenome to other formats")
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-g", "--to-gfa",
              is_flag=True,
              help="write the graph in GFAv1 format to stdout")
@common_options
def view(con, to_gfa, threads, progress):
    set_duckdb_threads(con, threads)
    if to_gfa:
        print("H\tVN:Z:1.0")
        con.execute("""
        SELECT 'S', name, sequence FROM segment
        """).fetchdf().to_csv(sys.stdout, sep="\t", header=False, index=False)
        con.execute("""
        SELECT 'L', from_segment.name, from_orientation, to_segment.name, to_orientation FROM link
        INNER JOIN segment AS from_segment ON from_segment.id=link.from_segment
        INNER JOIN segment AS to_segment ON to_segment.id=link.to_segment
        """).fetchdf().to_csv(sys.stdout, sep="\t", header=False, index=False)
        con.execute("""
        SELECT 'P', ANY_VALUE(path.name), string_agg(segment.name || segment_orientation, ',' ORDER BY start)
        FROM path
        INNER JOIN path_segment ON path.id=path_segment.path_id
        INNER JOIN segment ON segment.id=path_segment.segment_id
        GROUP BY path.id;
        """).fetchdf().to_csv(sys.stdout, sep="\t", header=False, index=False)

if __name__ == "__main__":
    main()
