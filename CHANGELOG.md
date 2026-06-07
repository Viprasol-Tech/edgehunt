# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [0.1.0] - 2025

### Added
- Initial release of edgehunt: open-source prediction-market edge & arbitrage engine.
- `Market` / `Opportunity` pydantic models with cents-based binary book validation.
- Fee models: Kalshi price-dependent per-contract fee and Polymarket-style percentage fee.
- EV math: implied probability, fee-adjusted expected value, and break-even probability.
- Kelly sizing: full / fractional Kelly with bankroll stake and a no-bet-on-no-edge rule.
- Arbitrage: single-market (`YES + NO < $1`) and cross-venue lock-in detection, fee-adjusted.
- Fair-value mispricing signals from model probabilities vs market price.
- `Scanner` that merges and ranks all opportunity types onto one board.
- `MarketFeed` protocol with a deterministic offline `FakeFeed` and a `LiveFeed` adapter stub.
- Colourful, ASCII-safe `rich` terminal dashboard.
- Typer CLI: `scan`, `ev`, `kelly`, `arb`, `version`.
- 85 unit tests; strict mypy, ruff, and offline-by-default execution.
