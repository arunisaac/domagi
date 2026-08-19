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

import io

from click.testing import CliRunner
import duckdb
import pandas as pd
from pandas.testing import assert_frame_equal
from pathlib import Path
import pytest

from domagi.domagi import main

def assert_gfa_equal(expected, actual):
    def invert_orientation(orientation):
        return "-" if orientation=="+" else "+"

    def process_gfa_line(line):
        fields = line.split("\t")
        if fields[0] == "L":
            _, from_segment, from_orientation, to_segment, to_orientation = fields[:5]
            if from_segment <= to_segment:
                return ["L", from_segment, from_orientation, to_segment, to_orientation]
            else:
                return ["L",
                        to_segment, invert_orientation(to_orientation),
                        from_segment, invert_orientation(from_orientation)]
        elif fields[0] == "P":
            return fields[:3]
        else:
            return fields

    def read_gfa_file(file):
        return sorted([process_gfa_line(line.rstrip())
                       for line in file.readlines()])

    assert read_gfa_file(expected) == read_gfa_file(actual)

def build_db(test_data_file, duckdb_path):
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    return duckdb_path

@pytest.fixture(scope="session")
def domagi_db_test1(tmp_path_factory):
    return build_db(Path("test-data/test1.gfa"),
                    tmp_path_factory.mktemp("db") / "test1.db")

@pytest.fixture(scope="session")
def domagi_db_test2(tmp_path_factory):
    return build_db(Path("test-data/test2.gfa"),
                    tmp_path_factory.mktemp("db") / "test2.db")

@pytest.fixture(scope="session")
def domagi_db_test3(tmp_path_factory):
    return build_db(Path("test-data/test3.gfa"),
                    tmp_path_factory.mktemp("db") / "test3.db")

@pytest.fixture(scope="session")
def domagi_db_testcrush(tmp_path_factory):
    return build_db(Path("test-data/test-crush.gfa"),
                    tmp_path_factory.mktemp("db") / "test-crush.db")

@pytest.mark.parametrize("domagi_db_name, chop_to, expected_output",
                         [("domagi_db_test3",
                           1,
                           Path("test-data/expected-output/test3-chop-1.gfa")),
                          ("domagi_db_test3",
                           2,
                           Path("test-data/expected-output/test3-chop-2.gfa")),
                          ("domagi_db_test3",
                           3,
                           Path("test-data/expected-output/test3-chop-3.gfa")),
                          ("domagi_db_test3",
                           4,
                           Path("test-data/expected-output/test3-chop-4.gfa"))])
def test_domagi_chop(tmp_path, request, domagi_db_name, chop_to, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    output_duckdb_path = tmp_path / f"{domagi_db.stem}-output.db"
    runner = CliRunner()
    result = runner.invoke(main, ["chop",
                                  "--db", domagi_db,
                                  "--chop-to", chop_to,
                                  "--out", output_duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["view",
                                  "--to-gfa",
                                  "--db", output_duckdb_path])
    assert result.exit_code == 0
    with open(expected_output) as file:
        assert_gfa_equal(file, io.StringIO(result.stdout))

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_testcrush",
                           Path("test-data/expected-output/test-crush.gfa"))])
def test_domagi_crush(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    output_duckdb_path = tmp_path / f"{domagi_db.stem}-output.db"
    runner = CliRunner()
    result = runner.invoke(main, ["crush",
                                  "--db", domagi_db,
                                  "--out", output_duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["view",
                                  "--to-gfa",
                                  "--db", output_duckdb_path])
    assert result.exit_code == 0
    with open(expected_output) as file:
        assert_gfa_equal(file, io.StringIO(result.stdout))

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1-depth")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2-depth")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3-depth"))])
def test_domagi_depth(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    expected = (pd.read_csv(expected_output, sep="\t")
                .sort_values(by="#path", ignore_index=True))
    runner = CliRunner()
    result = runner.invoke(main, ["depth",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    assert_frame_equal(expected,
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t")
                       .sort_values(by="#path",
                                    ignore_index=True),
                       check_dtype=False)
    for _, row in expected.iterrows():
        per_path_expected = pd.DataFrame([row]).reset_index(drop=True)
        path = row["#path"]
        result = runner.invoke(main, ["depth",
                                      "--db", domagi_db,
                                      "--path", path])
        assert result.exit_code == 0
        assert_frame_equal(per_path_expected,
                           pd.read_csv(io.StringIO(result.stdout),
                                       sep="\t")
                           .sort_values(by="#path",
                                        ignore_index=True),
                           check_dtype=False)

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1-depth-graph-depth")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2-depth-graph-depth")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3-depth-graph-depth"))])
def test_domagi_depth_graph_depth(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["depth",
                                  "--graph-depth-table",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t")
                       .sort_values(by="#node.id",
                                    ignore_index=True),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t")
                       .sort_values(by="#node.id",
                                    ignore_index=True),
                       check_dtype=False)

@pytest.mark.parametrize("domagi_db_name, bed_windows, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/test1-bed-windows"),
                           Path("test-data/expected-output/test1-depth-bed-windows")),
                          ("domagi_db_test2",
                           Path("test-data/test2-bed-windows"),
                           Path("test-data/expected-output/test2-depth-bed-windows")),
                          ("domagi_db_test3",
                           Path("test-data/test3-bed-windows"),
                           Path("test-data/expected-output/test3-depth-bed-windows"))])
def test_domagi_depth_bed_windows(tmp_path, request, domagi_db_name, bed_windows, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["depth",
                                  "--bed-input", bed_windows,
                                  "--db", domagi_db])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t"),
                       pd.read_csv(io.StringIO(result.stdout), sep="\t"),
                       check_dtype=False)

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1-matrix")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2-matrix")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3-matrix"))])
def test_domagi_matrix(tmp_path, request, domagi_db_name, expected_output):
    def read_matrix_file(file):
        return (file.readline().rstrip(),
                [line.rstrip() for line in sorted(file.readlines())])

    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["matrix",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    with open(expected_output) as file:
        expected_header, expected_lines = read_matrix_file(file)
    with io.StringIO(result.stdout) as file:
        actual_header, actual_lines = read_matrix_file(file)
    assert expected_header == actual_header
    assert expected_lines == actual_lines

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1-overlap")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2-overlap")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3-overlap"))])
def test_domagi_overlap(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    paths = [path for path, in (duckdb.connect(domagi_db, True)
                                .execute("SELECT name FROM path")
                                .fetchall())]
    result = runner.invoke(main, ["overlap",
                                  "--db", domagi_db,
                                  *sum([["--path", path] for path in paths],
                                       [])])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t")
                       .sort_values(by=["#path", "path.touched"],
                                    ignore_index=True),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t")
                       .sort_values(by=["#path", "path.touched"],
                                    ignore_index=True),
                       check_dtype=False)
    # Test passing in the paths through a file.
    paths_file = tmp_path / "paths"
    with open(paths_file, "w") as file:
        for path in paths:
            print(path, file=file)
    result = runner.invoke(main, ["overlap",
                                  "--db", domagi_db,
                                  "--paths", paths_file])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t")
                       .sort_values(by=["#path", "path.touched"],
                                    ignore_index=True),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t")
                       .sort_values(by=["#path", "path.touched"],
                                    ignore_index=True),
                       check_dtype=False)

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1-paths")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2-paths")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3-paths"))])
def test_domagi_paths(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["paths",
                                  "--list-paths",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t", header=None),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t",
                                   header=None),
                       check_dtype=False)

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1.fa")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2.fa")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3.fa"))])
def test_domagi_paths_fasta(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["paths",
                                  "--fasta",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    with open(expected_output) as file:
        assert result.stdout == file.read()

@pytest.mark.parametrize("domagi_db_name, expected_output",
                         [("domagi_db_test1",
                           Path("test-data/expected-output/test1-stats")),
                          ("domagi_db_test2",
                           Path("test-data/expected-output/test2-stats")),
                          ("domagi_db_test3",
                           Path("test-data/expected-output/test3-stats"))])
def test_domagi_stats(tmp_path, request, domagi_db_name, expected_output):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["stats",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t"),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t"),
                       check_dtype=False)

@pytest.mark.parametrize("domagi_db_name, original_gfa_file",
                         [("domagi_db_test1",
                           Path("test-data/test1.gfa")),
                          ("domagi_db_test2",
                           Path("test-data/test2.gfa")),
                          ("domagi_db_test3",
                           Path("test-data/test3.gfa"))])
def test_domagi_view(tmp_path, request, domagi_db_name, original_gfa_file):
    domagi_db = request.getfixturevalue(domagi_db_name)
    runner = CliRunner()
    result = runner.invoke(main, ["view",
                                  "--to-gfa",
                                  "--db", domagi_db])
    assert result.exit_code == 0
    with open(original_gfa_file) as expected:
        assert_gfa_equal(expected, io.StringIO(result.stdout))

def test_error_on_missing_paths(tmp_path, domagi_db_test1):
    runner = CliRunner()
    result = runner.invoke(main, ["depth",
                                  "--db", domagi_db_test1,
                                  "--path", "xx"])
    assert result.exit_code == 1 and result.output == "Paths ['xx'] not found\n"
    result = runner.invoke(main, ["overlap",
                                  "--db", domagi_db_test1,
                                  "--path", "xx"])
    assert result.exit_code == 1 and result.output == "Paths ['xx'] not found\n"
