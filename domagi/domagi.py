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

common_options = click.option("-t", "--threads", "threads",
                              type=click.INT,
                              help="number of threads (default: number of CPUs)")

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

@main.command()
@click.option("-g", "--gfa", "gfa",
              metavar="FILE",
              required=True,
              help="GFAv1 pangenome")
@click.option("-o", "--out", "db",
              type=click.Path(),
              required=True,
              help="output pangenome duckdb database")
@common_options
def build(gfa, db, threads):
    with connect_duckdb(db, threads) as con:
        con.execute(read_sql("schema.sql"))
    with connect_duckdb(db, threads) as con:
        con.execute(read_sql("pre-import.sql"))
    subprocess.run([shutil.which("domagi_importgfa"), gfa, db],
                   env={"OMP_NUM_THREADS": str(threads)} if threads else None)
    with connect_duckdb(db, threads) as con:
        con.execute(read_sql("post-import.sql"))

@main.command()
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-o", "--out", "outfile",
              type=click.Path(),
              required=True,
              help="path to output pangenome duckdb database")
@common_options
def crush(con, outfile, threads):
    set_duckdb_threads(con, threads)
    con.execute(f"""
    ATTACH '{outfile}' AS output_db (READ_WRITE);
    
    CREATE TABLE output_db.segment AS
      SELECT segment.id, name, regexp_replace(sequence, 'N+', 'N', 'g') AS sequence
      FROM segment;

    CREATE TABLE output_db.link AS
      SELECT * FROM link;

    CREATE TABLE output_db.path AS
      SELECT * FROM path;

    CREATE TABLE output_db.path_segment AS
      SELECT * FROM path_segment
      ORDER BY path_id, start, "end"
    """)

@main.command()
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
def depth(con, graph_depth_table, paths, bed_input, threads):
    set_duckdb_threads(con, threads)
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

@main.command()
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
def extract(con, outfile, segment_name, path_range, steps, threads):
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
          INNER JOIN link ON from_segment=id
          WHERE distance<?
      )
      SELECT id FROM cte;
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

# TODO: Add synopses for commands.
@main.command()
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@common_options
def matrix(con, threads):
    set_duckdb_threads(con, threads)
    segment_count, = con.execute("SELECT COUNT() FROM segment").fetchone()
    df = con.execute(read_sql("matrix.sql")).fetchdf()
    print(segment_count, segment_count, df.shape[0])
    df.to_csv(sys.stdout, sep=" ", header=False, index=False)

@main.command()
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
def paths(con, list_paths, fasta, threads):
    set_duckdb_threads(con, threads)
    if list_paths:
        for name, in con.execute("SELECT name FROM path").fetchall():
            print(name)
    elif fasta:
        for name, sequence in con.execute("""
        SELECT ANY_VALUE(path_name),
               string_agg(sequence, '' ORDER BY position)
        FROM path
        INNER JOIN segment ON segment.id = path_segment.segment_id
        GROUP BY path_id
        """).fetchall():
            print(f">{name}")
            print(sequence)

@main.command()
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
# The --summarize flag seems to be a no-op in odgi.
@click.option("-S", "--summarize",
              is_flag=True,
              hidden=True)
@common_options
def stats(con, summarize, threads):
    set_duckdb_threads(con, threads)
    print("\t".join(["#length", "nodes", "edges", "paths", "steps"]))
    length, = con.execute("SELECT sum(len(sequence)) FROM segment").fetchone()
    nodes, = con.execute("SELECT COUNT() FROM segment").fetchone()
    edges, = con.execute("SELECT COUNT() FROM link").fetchone()
    paths, = con.execute("SELECT COUNT() FROM path").fetchone()
    steps, = con.execute("SELECT COUNT() FROM path_segment").fetchone()
    print("\t".join([str(length), str(nodes), str(edges),
                     str(paths), str(steps)]))

@main.command()
@click.option("-i", "--db", "--idx", "con",
              type=DuckDBParamType(),
              required=True,
              help="pangenome duckdb database")
@click.option("-g", "--to-gfa",
              is_flag=True,
              help="write the graph in GFAv1 format to stdout")
@common_options
def view(con, to_gfa, threads):
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
