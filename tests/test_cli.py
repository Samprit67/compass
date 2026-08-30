import json

from compass.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "compass" in result.stdout


def test_data_info():
    result = runner.invoke(app, ["data", "info"])
    assert result.exit_code == 0
    assert "O*NET version" in result.stdout


def test_major_lookup_by_partial_name():
    result = runner.invoke(app, ["major", "Computer Science"])
    assert result.exit_code == 0
    assert "Interest profile" in result.stdout
    assert "Where it leads" in result.stdout


def test_major_ambiguous_name_reports_options():
    result = runner.invoke(app, ["major", "engineering"])
    assert result.exit_code == 1
    assert "matches several" in result.stdout


def test_score_from_file(tmp_path):
    payload = {"answers": {f"i{k}": 4 for k in range(1, 11)}, "dealbreakers": []}
    f = tmp_path / "a.json"
    f.write_text(json.dumps(payload))
    result = runner.invoke(app, ["score", str(f), "--top", "5"])
    assert result.exit_code == 0
    assert "Best-fitting majors" in result.stdout


def test_score_json_output(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({"answers": {"i1": 4}}))
    result = runner.invoke(app, ["score", str(f), "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert "results" in parsed and "profile" in parsed


def test_compare_command():
    result = runner.invoke(app, ["compare", "Finance", "Studio Art"])
    assert result.exit_code == 0
    assert "Finance" in result.stdout and "Studio Art" in result.stdout
