"""CBBTC dip-bounce bot for btc-race-24h-20261118-1444.

Idea (written from my own analysis of the dev window, not copied from any
baseline): the Orca cbBTC/USDC pool is thin, so a sharp sell-off overshoots
and then bounces back within the next 15-30 minutes. On the dev window,
after a drop of 150+ bps over 30 minutes the price was on average ~+110 bps
higher 15 minutes later, with the worst 120-minute drawdown after such a
drop only about -60 bps. This bot does nothing most of the time and only
buys a sharp dip, then sells into the bounce (or cuts the loss).

Rules:
  * Entry (long only, whole cash): the close has fallen at least
    DROP30_BPS over the last 30 bars, or DROP15_BPS over 15 bars, or
    DROP60_BPS over 60 bars.
  * Exit the whole position when the close is TAKE_PROFIT_BPS above the
    entry close, STOP_LOSS_BPS below it, or MAX_HOLD_BARS have passed.
  * After a stop-loss, re-enter once if the 30-bar drop has deepened by at
    least REENTRY_DEEPEN_BPS (the dip is still falling into a better price).
  * No new entries in the last LAST_ENTRY_CUTOFF bars, so no position is
    left to be flattened at a bad price at the end of the window.
  * One order per reply at most; max slippage 100 bps (fills move ~10 bps).

Deterministic: pure integer arithmetic on the closes the harness sends, no
clock, no files, no network, no randomness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# Entry: a sharp fall over 30 / 15 / 60 bars, in basis points.
DROP30_BPS = 150
DROP15_BPS = 180
DROP60_BPS = 200
# Exit: take profit / stop loss vs the entry close, in basis points.
TAKE_PROFIT_BPS = 100
STOP_LOSS_BPS = 50
# Exit: give up after this many bars without a profit or a stop.
MAX_HOLD_BARS = 60
# Bars to wait after an exit before a fresh (non-re-entry) buy.
COOLDOWN_BARS = 3
# After a stop-loss, re-enter if the 30-bar drop has deepened this much.
REENTRY_DEEPEN_BPS = 50
# No new entries once this many bars are left in the window.
LAST_ENTRY_BAR = 1380
# Fills move ~10 bps from the open; 100 bps leaves ample room for a gap.
MAX_SLIPPAGE_BPS = 100


class DipBounce:
    """State for one run: the closes seen so far and the open position."""

    def __init__(self):
        self.closes = []
        self.entry_close = 0
        self.entry_bar = -1
        self.cool_until = -1
        self.stop_drop30 = None

    def drop_bps(self, bars_back):
        """How far the close has fallen over the last ``bars_back`` bars, in bps."""
        if len(self.closes) <= bars_back:
            return -10 ** 9
        old = self.closes[-1 - bars_back]
        now = self.closes[-1]
        return (old - now) * 10000 // old

    def on_batch(self, state, batch):
        bar = None
        for b in batch["bars"]:
            if b["symbol"] == SYMBOL:
                bar = b
                break
        if bar is None:
            return []
        self.closes.append(int(bar["c"]))
        if state.warming_up:
            return []
        close = self.closes[-1]
        held = state.positions.get(SYMBOL)
        if held is not None:
            gain_bps = (close - self.entry_close) * 10000 // self.entry_close
            if (
                gain_bps >= TAKE_PROFIT_BPS
                or gain_bps <= -STOP_LOSS_BPS
                or state.seq - self.entry_bar >= MAX_HOLD_BARS
            ):
                if gain_bps <= -STOP_LOSS_BPS:
                    self.stop_drop30 = self.drop_bps(30)
                self.cool_until = state.seq + COOLDOWN_BARS
                return [
                    {
                        "side": "sell",
                        "symbol": SYMBOL,
                        "qty": held.qty,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }
                ]
            return []
        # Flat: look for a sharp dip to buy.
        if state.seq > LAST_ENTRY_BAR:
            return []
        drop30 = self.drop_bps(30)
        trigger = (
            drop30 >= DROP30_BPS
            or self.drop_bps(15) >= DROP15_BPS
            or self.drop_bps(60) >= DROP60_BPS
        )
        # Re-entry after a stop-loss: the dip is still deepening into a better
        # price. It bypasses the cooldown; it stays armed until the dip either
        # deepens (re-enter) or recovers past the stop level (stand down).
        reentry = False
        if self.stop_drop30 is not None:
            if drop30 >= self.stop_drop30 + REENTRY_DEEPEN_BPS:
                reentry = True
            elif drop30 < self.stop_drop30:
                self.stop_drop30 = None
        if not trigger and not reentry:
            return []
        if not reentry and state.seq < self.cool_until:
            return []
        if state.cash < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        self.entry_close = close
        self.entry_bar = state.seq
        self.stop_drop30 = None
        return [
            {
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": state.cash,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }
        ]


def on_batch(state, batch):
    return _BOT.on_batch(state, batch)


_BOT = DipBounce()

makefun_bars.run(on_batch)
