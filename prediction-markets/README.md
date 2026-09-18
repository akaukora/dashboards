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

**Kalshi** reports no P&L. It is reconstructed:

- unrealized = contracts × current price − cost basis, where the current price
  is `last_price` for a Yes position and its complement for a No position
- realized = settlement revenue − cost basis − fees

`last_price` is the last trade, which in a thin market can sit well away from
the current bid/ask. So a Kalshi position's value can look stale in a way a
Polymarket one does not. Switching to the bid/ask midpoint is a one-line change
in `fetch_data.py` if that turns out to matter.

Fees are also handled differently on each side — Kalshi charges explicit
per-contract maker/taker fees that are subtracted here; Polymarket's are already
inside the figures it reports.

## Open question

The preview snapshot computes total P&L of **+$206.14** (+$171.95 realized,
+$34.19 unrealized). The Polymarket profile page shows **+$143.22**. Position
value reconciles exactly ($186.19 both ways), so the gap is in how the profile
aggregates P&L, not in the position data. Worth checking against a real fetch —
the profile figure may be scoped to a time window, or may exclude something the
closed-positions endpoint includes.
