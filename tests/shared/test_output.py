"""Tests for gaad.shared.output."""

import json

from gaad.shared.output import OutputFormat, render_csv, render_json


class TestOutputFormat:
    def test_values(self):
        assert OutputFormat.table == "table"
        assert OutputFormat.json == "json"
        assert OutputFormat.csv == "csv"


class TestRenderJson:
    def test_renders_dict(self, capsys):
        render_json({"key": "value"})
        out = capsys.readouterr().out
        assert json.loads(out) == {"key": "value"}

    def test_renders_list(self, capsys):
        render_json([{"a": 1}, {"a": 2}])
        out = capsys.readouterr().out
        assert json.loads(out) == [{"a": 1}, {"a": 2}]


class TestRenderCsv:
    def test_renders_rows(self, capsys):
        render_csv([{"id": "1", "name": "Foo"}], fieldnames=["id", "name"])
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        assert lines[0] == "id,name"
        assert lines[1] == "1,Foo"
