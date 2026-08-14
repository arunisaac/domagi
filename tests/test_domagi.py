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
    def process_gfa_line(line):
        fields = line.split("\t")
        if fields[0] == "L":
            return fields[:5]
        elif fields[0] == "P":
            return fields[:3]
        else:
            return fields

    def read_gfa_file(file):
        return sorted([process_gfa_line(line.rstrip())
                       for line in file.readlines()])

    assert read_gfa_file(expected) == read_gfa_file(actual)

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test-crush.gfa"),
                           Path("test-data/expected-output/test-crush.gfa"))])
def test_domagi_crush(tmp_path, test_data_file, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    crushed_duckdb_path = tmp_path / f"{test_data_file.stem}-crushed.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["crush",
                                  "--db", duckdb_path,
                                  "--out", crushed_duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["view",
                                  "--to-gfa",
                                  "--db", crushed_duckdb_path])
    assert result.exit_code == 0
    with open(expected_output) as file:
        assert_gfa_equal(file, io.StringIO(result.stdout))

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1-depth")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2-depth")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3-depth"))])
def test_domagi_depth(tmp_path, test_data_file, expected_output):
    expected = (pd.read_csv(expected_output, sep="\t")
                .sort_values(by="#path", ignore_index=True))
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["depth",
                                  "--db", duckdb_path])
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
                                      "--db", duckdb_path,
                                      "--path", path])
        assert result.exit_code == 0
        assert_frame_equal(per_path_expected,
                           pd.read_csv(io.StringIO(result.stdout),
                                       sep="\t")
                           .sort_values(by="#path",
                                        ignore_index=True),
                           check_dtype=False)

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1-depth-graph-depth")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2-depth-graph-depth")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3-depth-graph-depth"))])
def test_domagi_depth_graph_depth(tmp_path, test_data_file, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["depth",
                                  "--graph-depth-table",
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t")
                       .sort_values(by="#node.id",
                                    ignore_index=True),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t")
                       .sort_values(by="#node.id",
                                    ignore_index=True),
                       check_dtype=False)

@pytest.mark.parametrize("test_data_file, bed_windows, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/test1-bed-windows"),
                           Path("test-data/expected-output/test1-depth-bed-windows")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/test2-bed-windows"),
                           Path("test-data/expected-output/test2-depth-bed-windows")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/test3-bed-windows"),
                           Path("test-data/expected-output/test3-depth-bed-windows"))])
def test_domagi_depth_bed_windows(tmp_path, test_data_file, bed_windows, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["depth",
                                  "--bed-input", bed_windows,
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t"),
                       pd.read_csv(io.StringIO(result.stdout), sep="\t"),
                       check_dtype=False)

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1-matrix")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2-matrix")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3-matrix"))])
def test_domagi_matrix(tmp_path, test_data_file, expected_output):
    def read_matrix_file(file):
        return (file.readline().rstrip(),
                [line.rstrip() for line in sorted(file.readlines())])

    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["matrix",
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    with open(expected_output) as file:
        expected_header, expected_lines = read_matrix_file(file)
    with io.StringIO(result.stdout) as file:
        actual_header, actual_lines = read_matrix_file(file)
    assert expected_header == actual_header
    assert expected_lines == actual_lines

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1-overlap")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2-overlap")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3-overlap"))])
def test_domagi_overlap(tmp_path, test_data_file, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    paths = [path for path, in (duckdb.connect(duckdb_path, True)
                                .execute("SELECT name FROM path")
                                .fetchall())]
    result = runner.invoke(main, ["overlap",
                                  "--db", duckdb_path,
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
                                  "--db", duckdb_path,
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

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1-paths")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2-paths")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3-paths"))])
def test_domagi_paths(tmp_path, test_data_file, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["paths",
                                  "--list-paths",
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t", header=None),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t",
                                   header=None),
                       check_dtype=False)

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1.fa")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2.fa")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3.fa"))])
def test_domagi_paths_fasta(tmp_path, test_data_file, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["paths",
                                  "--fasta",
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    with open(expected_output) as file:
        assert result.stdout == file.read()

@pytest.mark.parametrize("test_data_file, expected_output",
                         [(Path("test-data/test1.gfa"),
                           Path("test-data/expected-output/test1-stats")),
                          (Path("test-data/test2.gfa"),
                           Path("test-data/expected-output/test2-stats")),
                          (Path("test-data/test3.gfa"),
                           Path("test-data/expected-output/test3-stats"))])
def test_domagi_stats(tmp_path, test_data_file, expected_output):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["stats",
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    assert_frame_equal(pd.read_csv(expected_output, sep="\t"),
                       pd.read_csv(io.StringIO(result.stdout),
                                   sep="\t"),
                       check_dtype=False)

@pytest.mark.parametrize("test_data_file",
                         [Path("test-data/test1.gfa"),
                          Path("test-data/test2.gfa"),
                          Path("test-data/test3.gfa")])
def test_domagi_view(tmp_path, test_data_file):
    duckdb_path = tmp_path / f"{test_data_file.stem}.db"
    runner = CliRunner()
    result = runner.invoke(main, ["build",
                                  "--gfa", test_data_file,
                                  "--out", duckdb_path])
    assert result.exit_code == 0
    result = runner.invoke(main, ["view",
                                  "--to-gfa",
                                  "--db", duckdb_path])
    assert result.exit_code == 0
    with open(test_data_file) as expected:
        assert_gfa_equal(expected, io.StringIO(result.stdout))
