from __future__ import annotations

from typer.testing import CliRunner

from edgehunt import __version__
from edgehunt.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_scan_renders_board() -> None:
    result = runner.invoke(app, ["scan", "--bankroll", "2000"])
    assert result.exit_code == 0
    assert "ranked opportunities" in result.stdout
    assert "ARB" in result.stdout


def test_scan_is_ascii_safe() -> None:
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0
    # No unicode arrows in the output.
    for ch in ("→", "↑", "↓", "←"):
        assert ch not in result.stdout


def test_ev_command() -> None:
    result = runner.invoke(app, ["ev", "0.6", "50"])
    assert result.exit_code == 0
    assert "Expected value" in result.stdout


def test_kelly_command_with_edge() -> None:
    result = runner.invoke(app, ["kelly", "0.6", "40"])
    assert result.exit_code == 0
    assert "Stake" in result.stdout


def test_kelly_command_no_edge() -> None:
    result = runner.invoke(app, ["kelly", "0.4", "50"])
    assert result.exit_code == 0
    assert "No edge" in result.stdout


def test_arb_command_positive() -> None:
    result = runner.invoke(app, ["arb", "45", "48"])
    assert result.exit_code == 0
    assert "Arbitrage" in result.stdout


def test_arb_command_negative() -> None:
    result = runner.invoke(app, ["arb", "60", "55"])
    assert result.exit_code == 0
    assert "No arbitrage" in result.stdout
