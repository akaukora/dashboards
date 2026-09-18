# Prediction markets dashboard

Polymarket and Kalshi positions in one view, following the same pattern as the
other dashboards in `akaukora/dashboards`: a scheduled workflow writes a
`data.json` snapshot, the page renders it.

Lands at `akaukora.github.io/dashboards/prediction-markets/`.

## Files

| Path | What it is |
|---|---|
| `prediction-markets/index.html` | The page. Self-contained, no external requests. |
| `prediction-markets/fetch_data.py` | Pulls both venues, writes `data.json`. |
| `prediction-markets/data.json` | Current snapshot. **Preview values until the first run.** |
| `.github/workflows/update-predictions.yml` | Refresh, twice daily. |

Copy `prediction-markets/` to the repo root and merge the workflow into the
existing `.github/workflows/`.

## Setup

Polymarket needs nothing — the wallet address is already in the workflow and the
Data API is public.

For Kalshi, create a key at <https://kalshi.com/account/profile> → API Keys:

1. Leave **Read all data `read`** checked, uncheck **Full access `write`**.
   A read-scoped key cannot place or cancel orders.
2. Save the private key when it appears — it is shown once and cannot be
   retrieved again.
3. In the repo, Settings → Secrets and variables → Actions, add:
   - `KALSHI_KEY_ID` — the key's UUID
   - `KALSHI_PRIVATE_KEY` — the whole PEM block, `-----BEGIN` through `-----END`

Then run the workflow manually once (Actions → Update prediction markets
dashboard → Run workflow) to confirm both venues load.

Until those secrets exist the workflow still succeeds — the page shows
Polymarket alone and says Kalshi has no credentials.

## Running it locally

```bash
export POLYMARKET_WALLET=0x7a373de589a0f6ac9f1fa9dde84296af2adbb10b
export KALSHI_KEY_ID=...                      # optional
export KALSHI_PRIVATE_KEY="$(cat kalshi.pem)" # optional
pip install requests cryptography
python prediction-markets/fetch_data.py
python -m http.server -d prediction-markets 8000
```

The page reads `data.json` over `fetch()`, so it needs a server — opening the
file directly with `file://` will not work.

## How the two venues differ

They are not the same measurement, and the page does not pretend otherwise.

**Polymarket** reports P&L itself. `cashPnl` and `percentPnl` come straight off
the API and are passed through untouched, so open-position numbers match the
profile page exactly.

**Kalshi** reports no P&L. It is reconstructed, and the reconstruction is built
to match what the Kalshi app's own portfolio screens show:

- cost basis = `market_exposure_dollars` **plus** `fees_paid_dollars`. Exposure
  alone excludes fees, but the app's "Cost" column includes them and its "Total
  return" is measured against that, so the fees are added back.
- current value = contracts × `last_price_dollars` for a Yes position, or its
  complement for a No position. The last trade is used rather than the bid/ask
  midpoint specifically because that is what the app's "Market value" uses.
  The midpoint is the better mark on a thin market; it is the fallback here, and
  `kalshi_price()` swaps the order in two lines if you'd rather have it.
- realized P&L is **cash basis from fills**, not from settlements. See below.

Both were verified against the app: all four open positions and all five settled
markets reconcile to the cent.

### Why realized P&L comes from fills

A market exited by *selling* before it resolved has a settlement payout of zero,
or no settlement row at all. Deriving realized P&L from settlements therefore
books the entire cost as a loss and drops traded-out positions altogether — the
first version of this script reported the Fed rate hike market as **−$88.45**
when it was actually **+$46.10**, and missed the Ossoff market entirely.

So `fetch_data.py` walks `/portfolio/fills` (plus `/historical/fills` for older
ones): money out on buys, money in on sells, plus any settlement payout. That is
the same cash-in/cash-out framing as the app's Total cost / Total payout / Total
return columns, and it holds whether a market was sold out of, held to
settlement, or both.

One trap inside that: **on a sell, `outcome_side` is not the side you held.**
Selling Yes is booked against the No side of the book, so reading the price field
that `outcome_side` names prices the exit at its complement — a 13c sale becomes
87c. That turned a +$0.98 round trip into +$170.48. The side of each market is
therefore taken from its *buy* fills only, and every fill in that market is then
priced from that side's field. Markets held to settlement were never affected,
which is why the bug only showed on positions that were traded out.

Each closed entry carries `sale_proceeds`, `settlement_payout`, `sold` and `fees`
alongside the totals, so a future mismatch can be traced to the sell leg or the
settlement leg without re-deriving anything.

Fees differ by venue in one more way: Kalshi's per-contract maker/taker fees are
explicit and handled above, while Polymarket's are already inside the numbers it
reports.

### Missing prices are never shown as zero

If Kalshi returns no usable quote for a market, the position is held at cost and
flagged `price_basis: "unavailable"` rather than valued at zero. A zero price
renders as a total loss, which is how the first run showed a −100% on two
perfectly healthy positions.

## Returns

Every position and settled market now carries `opened_at`, `days_held` and
`annualized`, and the totals carry `staked`, `roi` and `irr`.

**Entry dates** come from the trade history, not the position endpoints, which
don't have them: Kalshi from the first buy fill per market, Polymarket from the
first BUY row in `/activity` for that `conditionId`.

**Per-market annualized** is `(1 + roi) ^ (365 / days) − 1`. It is suppressed
below a 7-day holding period and for total losses. Both suppressions are
deliberate: at 3 days the exponent is 122, so rounding noise and a one-tick
price move both come out as four-digit percentages, and a −100% result has no
finite annualized form at all. The dashboard prints `—` rather than a number
that would be read as information. Rates above +2,000% are shown as a ceiling
for the same reason.

**The headline figure is IRR** — money-weighted, over every dated buy, sell and
settlement, with open positions marked to market today. Two properties worth
knowing:

- It weights by size *and* by time, so it is not the average of the per-market
  rates. A large slow position moves it far more than a small fast one.
- It assumes capital is continuously redeployed at the same rate. That is
  precisely the assumption a run of short winning trades flatters — a 3% week
  annualizes to ~370%, which is arithmetically correct and not a forecast of
  anything. The same compounding runs in reverse on losses.

Polymarket's USDC `YIELD` rows are counted separately as `yield_earned` and kept
out of both figures. It is interest on idle balance, not a trading result, and
folding it in would quietly inflate the return.

A venue with no sign change in its flows — everything bought, nothing yet sold
or settled — returns `irr: null` rather than a fabricated number.

## Open question

Polymarket's own numbers total **+$206.13** (+$171.94 realized, +$34.19
unrealized). The profile page shows **+$143.22**. Position value reconciles
exactly ($186.19 three ways — computed, the `/value` endpoint, and the profile),
so the gap is in how the profile aggregates P&L, not in the position data. It
may be scoped to a time window, or exclude something `/closed-positions`
includes. Unresolved.
