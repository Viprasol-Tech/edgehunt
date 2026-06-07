"""Rich terminal dashboard for the ranked opportunity board.

Renders a colourful table -- green for profitable edges, red for negative --
with columns for venue(s), market, edge type, edge/EV, fee-adjusted profit and
the Kelly-sized stake. ASCII-only (no unicode arrows) so it copies cleanly into
a README and renders in any terminal.
"""

from __future__ import annotations

from rich.box import SQUARE
from rich.console import Console
from rich.table import Table
from rich.text import Text

from edgehunt.models import Opportunity, OpportunityType

_KIND_LABEL = {
    OpportunityType.SINGLE_MARKET_ARB: "ARB (1-mkt)",
    OpportunityType.CROSS_VENUE_ARB: "ARB (x-venue)",
    OpportunityType.MISPRICING: "MISPRICE",
}


def build_table(opportunities: list[Opportunity], bankroll: float) -> Table:
    """Build a Rich table for the given opportunities."""
    title = f"edgehunt :: ranked opportunities  (bankroll ${bankroll:,.0f})"
    table = Table(title=title, box=SQUARE, header_style="bold cyan", expand=False)
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Venue", style="magenta", no_wrap=True)
    table.add_column("Market", style="white", max_width=42)
    table.add_column("Type", no_wrap=True)
    table.add_column("Edge/EV", justify="right", no_wrap=True)
    table.add_column("Fee-adj profit", justify="right", no_wrap=True)
    table.add_column("Kelly stake", justify="right", no_wrap=True)

    if not opportunities:
        table.add_row("-", "-", "No edge found at current thresholds", "-", "-", "-", "-")
        return table

    for i, opp in enumerate(opportunities, start=1):
        profitable = opp.is_profitable
        colour = "green" if profitable else "red"

        if opp.kind is OpportunityType.MISPRICING:
            edge_text = f"{opp.edge * 100:+.1f}pts"
        else:
            edge_text = f"${opp.edge:.3f}/pr"

        type_text = Text(_KIND_LABEL[opp.kind], style="bold yellow")
        profit_text = Text(f"{opp.profit_per_dollar * 100:+.1f}%", style=colour)
        ev_text = Text(edge_text, style=colour)
        stake_text = f"${opp.stake:,.0f}" if opp.stake > 0 else "-"

        table.add_row(
            str(i),
            opp.venue,
            opp.question,
            type_text,
            ev_text,
            profit_text,
            stake_text,
        )
    return table


def render(
    opportunities: list[Opportunity],
    bankroll: float,
    console: Console | None = None,
) -> None:
    """Print the ranked opportunity board to the terminal."""
    console = console or Console()
    table = build_table(opportunities, bankroll)
    console.print(table)

    n_profit = sum(1 for o in opportunities if o.is_profitable)
    summary = Text()
    summary.append("Found ", style="dim")
    summary.append(str(len(opportunities)), style="bold")
    summary.append(" opportunities  ", style="dim")
    summary.append(f"({n_profit} profitable)", style="bold green" if n_profit else "dim")
    console.print(summary)


__all__ = ["build_table", "render"]
