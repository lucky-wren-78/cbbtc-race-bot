[![make.fun bounty: btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![CBBTC Race Bot rank on make.fun](https://make.fun/badge/btc-race-24h-20261118-1444/lucky-wren-78/cbbtc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![CBBTC Race Bot reward on make.fun](https://make.fun/badge/btc-race-24h-20261118-1444/lucky-wren-78/cbbtc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)

# CBBTC Race Bot — dip-bounce bot for btc-race-24h-20261118-1444

A bot that trades Coinbase Wrapped BTC (cbBTC) against USDC, minute by minute,
on the [make.fun](https://make.fun/bounty/btc-race-24h-20261118-1444) 24-hour race.
It starts with $1,000 of paper USDC, trades long only, and speaks the
`agent-fun/bars-replay/v1` protocol (`main.py`, Python 3.13, standard library only).

## Strategy

The Orca cbBTC/USDC pool is thin, so a sharp sell-off overshoots and then
bounces back within the next 15–30 minutes. On the published dev window, after
a drop of 150+ bps over 30 minutes the price was on average ~+110 bps higher
15 minutes later. This bot does nothing most of the time and only buys a sharp
dip, then sells into the bounce (or cuts the loss):

- **Entry** (whole cash): the close has fallen ≥150 bps over the last 30 bars,
  or ≥180 bps over 15 bars, or ≥200 bps over 60 bars.
- **Exit** the whole position when the close is +100 bps above the entry close
  (take profit), −50 bps below it (stop loss), or 60 bars have passed.
- **Re-entry**: after a stop-loss, buy again once if the 30-bar drop has
  deepened by a further 50 bps.
- **No new entries** in the last 60 bars, so no position is left to be
  flattened at a bad price at the end of the window.
- At most one order per reply; every order caps slippage at 100 bps
  (fills move ~10 bps from the open).

Deterministic: pure integer arithmetic on the closes the harness sends — no
clock, no files, no network, no randomness.

## Dev-window result

On the frozen dev window (1,440 one-minute bars, 17–18 Nov 2026), graded
locally with the kit's own fill model (fees, slippage and price impact):

- **Net PnL: +$7.90** (buy-and-hold on the same window: −$31.63)
- Max drawdown: 0.62%
- 1 round trip: bought bar 66 at $63,736.78, sold bar 81 at $64,292.02
- Fees paid: $0.80

## Files

- `main.py` — the bot (entrypoint)
- `vendor/makefun_bars.py` — byte-for-byte copy of the kit's Python SDK shim
- `LICENSE` — MIT
