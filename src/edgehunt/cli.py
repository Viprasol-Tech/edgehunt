"""edgehunt command-line interface (Typer).

Commands:

- ``edgehunt scan``    -- run the scanner over the FakeFeed and render the board.
- ``edgehunt ev``      -- expected value of a single position.
- ``edgehunt kelly``   -- Kelly stake for a single position.
- ``edgehunt arb``     -- single-market arb check for one YES/NO pair.
- ``edgehunt version`` -- print the installed version.
"""

from __future__ import annotations

import typer
from rich.console import Console

from edgehunt import __version__
from edgehunt.dashboard import render
from edgehunt.ev import break_even_probability, expected_value, implied_probability
from edgehunt.fees import fee_for_venue
from edgehunt.kelly import fractional_kelly
from edgehunt.kelly import stake as kelly_stake
from edgehunt.models import Market, Side
from edgehunt.scanner import Scanner

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="edgehunt -- find the edge in prediction markets.",
)
console = Console()


@app.command()
def scan(
    bankroll: float = typer.Option(1000.0, "--bankroll", "-b", help="Bankroll in dollars."),
    kelly_fraction: float = typer.Option(
        0.5, "--kelly-fraction", "-k", help="Fractional-Kelly multiplier (0.5 = half-Kelly)."
    ),
    min_edge: float = typer.Option(
        0.0, "--min-edge", "-m", help="Minimum edge to display (arb $/pair or mispricing pts)."
    ),
) -> None:
    """Scan the (offline) FakeFeed and render the ranked opportunity board."""
    from edgehunt.feed import FakeFeed

    scanner = Scanner(
        FakeFeed(),
        bankroll=bankroll,
        kelly_fraction=kelly_fraction,
        min_edge=min_edge,
    )
    opportunities = scanner.scan()
    render(opportunities, bankroll, console=console)


@app.command()
def ev(
    probability: float = typer.Argument(..., help="Your YES probability estimate (0..1)."),
    price: int = typer.Argument(..., help="Contract price in cents (1..99)."),
    side: Side = typer.Option(Side.YES, "--side", "-s", help="YES or NO."),
    venue: str = typer.Option("kalshi", "--venue", "-v", help="Venue for the fee model."),
) -> None:
    """Expected value (and break-even) of one contract, fee-adjusted."""
    fee = fee_for_venue(venue)
    value = expected_value(probability, price, side, fee)
    be = break_even_probability(price, side, fee)
    implied = implied_probability(price)
    colour = "green" if value > 0 else "red"
    console.print(f"Implied probability : [bold]{implied * 100:.1f}%[/bold]")
    console.print(f"Your probability    : [bold]{probability * 100:.1f}%[/bold]")
    console.print(f"Break-even (YES)    : [bold]{be * 100:.1f}%[/bold]")
    console.print(f"Expected value      : [{colour}]${value:+.4f}[/{colour}] per contract")


@app.command()
def kelly(
    probability: float = typer.Argument(..., help="Your YES probability estimate (0..1)."),
    price: int = typer.Argument(..., help="Contract price in cents (1..99)."),
    bankroll: float = typer.Option(1000.0, "--bankroll", "-b", help="Bankroll in dollars."),
    kelly_fraction: float = typer.Option(
        0.5, "--kelly-fraction", "-k", help="Fractional-Kelly multiplier."
    ),
    side: Side = typer.Option(Side.YES, "--side", "-s", help="YES or NO."),
) -> None:
    """Kelly bankroll fraction and dollar stake for one contract."""
    frac = fractional_kelly(probability, price, kelly_fraction, side)
    s = kelly_stake(bankroll, probability, price, kelly_fraction, side)
    if frac <= 0.0:
        console.print("[red]No edge -- recommended stake is $0 (do not bet).[/red]")
        return
    console.print(f"Kelly fraction : [bold]{frac * 100:.2f}%[/bold] of bankroll")
    console.print(f"Stake          : [bold green]${s:,.2f}[/bold green]")


@app.command()
def arb(
    yes_ask: int = typer.Argument(..., help="YES ask price in cents (1..99)."),
    no_ask: int = typer.Argument(..., help="NO ask price in cents (1..99)."),
    venue: str = typer.Option("kalshi", "--venue", "-v", help="Venue for the fee model."),
) -> None:
    """Single-market arbitrage check for a YES/NO pair."""
    from edgehunt.arbitrage import single_market_arbitrage

    market = Market(
        venue=venue,
        ticker="CLI-CHECK",
        question="cli arb check",
        yes_bid=max(1, yes_ask - 2),
        yes_ask=yes_ask,
        no_bid=max(1, no_ask - 2),
        no_ask=no_ask,
    )
    opp = single_market_arbitrage(market)
    if opp is None:
        cost = yes_ask + no_ask
        console.print(
            f"[red]No arbitrage[/red]: YES {yes_ask}c + NO {no_ask}c = {cost}c "
            "(>= 100c after fees)."
        )
        return
    console.print(f"[green]Arbitrage![/green] {opp.description}")
    console.print(f"Profit per dollar deployed: [bold green]{opp.profit_per_dollar * 100:+.2f}%")


@app.command()
def version() -> None:
    """Print the edgehunt version."""
    console.print(f"edgehunt {__version__}")


__all__ = ["app"]
