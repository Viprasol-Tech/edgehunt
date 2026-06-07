"""Generate the README demo image (a styled terminal screenshot) for `edgehunt scan`.

Renders the live opportunity board with rich and exports it as an SVG via
``Console.save_svg`` — a crisp, colored, GitHub-renderable terminal image with no
external screen-recording tools required.

Run:  PYTHONPATH=src python docs/make_demo.py
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from edgehunt.dashboard import render
from edgehunt.feed import FakeFeed
from edgehunt.scanner import Scanner

BANKROLL = 1000.0


def main() -> None:
    console = Console(record=True, width=100)
    scanner = Scanner(FakeFeed(), bankroll=BANKROLL, kelly_fraction=0.5)
    opportunities = scanner.scan()
    render(opportunities, BANKROLL, console=console)

    out = Path(__file__).resolve().parent / "assets" / "demo.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    console.save_svg(str(out), title="edgehunt scan")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
