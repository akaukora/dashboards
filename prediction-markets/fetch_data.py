#!/usr/bin/env python3
"""
Build data.json for the combined Polymarket + Kalshi dashboard.

Polymarket is read from the public Data API (no credentials).
Kalshi is read from the authenticated REST API using an RSA-PSS signed request.
The Kalshi half is skipped cleanly when no credentials are present, so the
dashboard works with Polymarket alone until the key is wired up.

Environment:
  POLYMARKET_WALLET     0x... wallet address        (required for Polymarket)
  KALSHI_KEY_ID         API key UUID                (optional)
  KALSHI_PRIVATE_KEY    RSA private key, PEM        (optional)

The private key is read from the environment only. It is never logged, never
written to data.json, and never echoed on failure.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import pathlib
import sys
import time
from typing import Any

import requests

POLY_BASE = "https://data-api.polymarket.com"
KALSHI_BASE = "https://external-api.kalshi.com"
KALSHI_PREFIX = "/trade-api/v2"

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data.json"

TIMEOUT = 30
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "prediction-markets-dashboard/1.0"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def num(value: Any, default: float = 0.0) -> float:
    """Kalshi returns fixed-point values as strings; Polymarket returns floats."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def opt(obj: dict, *keys) -> float | None:
    """First present, parseable key -> float. None when none of them are set.

    Kalshi serves prices as fixed-point dollar strings (last_price_dollars) and
    previously as integer cents (last_price). Reading a missing key as 0.0 is
    what silently priced positions at zero, so absence must stay distinguishable
    from a real zero.
    """
    for k in keys:
        if obj.get(k) is None:
            continue
        try:
            v = float(obj[k])
        except (TypeError, ValueError):
            continue
        return v / 100 if k.endswith(("_price", "_bid", "_ask")) else v
    return None


def kalshi_price(m: dict, is_yes: bool) -> tuple[float | None, str]:
    """Value per contract for the side held, and how it was derived.

    Uses the last traded price, because that is what Kalshi's own portfolio
    screen uses for "Market value" - matching it keeps the dashboard checkable
    against the app. last_price_dollars is always the YES price, so a NO
    position is worth its complement.

    The bid/ask midpoint is arguably the better mark on a thin market, where the
    last trade can sit well away from the live book. It is the fallback here
    rather than the default only so the two screens agree; swap the order below
    to prefer it.
    """
    last = opt(m, "last_price_dollars", "last_price")
    if last is not None and 0 < last < 1:
        return (last if is_yes else 1 - last), "last"

    side = "yes" if is_yes else "no"
    bid = opt(m, f"{side}_bid_dollars", f"{side}_bid")
    ask = opt(m, f"{side}_ask_dollars", f"{side}_ask")

    # A 0/1 book means "no quotes", not a real spread - that is not a 50c mid.
    if bid is not None and ask is not None and ask > bid and (ask - bid) <= 0.25:
        return (bid + ask) / 2, "mid"

    for one_sided in (bid, ask):
        if one_sided is not None and 0 < one_sided < 1:
            return one_sided, "quote"

    return None, "unavailable"


def iso(ts: Any) -> str | None:
    """Unix seconds or an ISO string -> ISO date string."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).date().isoformat()
    text = str(ts)
    if text.isdigit():
        return dt.datetime.fromtimestamp(int(text), tz=dt.timezone.utc).date().isoformat()
    return text[:10] if len(text) >= 10 else text


TODAY = dt.date.today()


def days_between(start: str | None, end: str | None) -> int | None:
    if not start:
        return None
    try:
        a = dt.date.fromisoformat(start[:10])
        b = dt.date.fromisoformat(end[:10]) if end else TODAY
    except ValueError:
        return None
    return max((b - a).days, 0)


def annualize(roi: float, days: int | None, floor_days: int = 7) -> float | None:
    """Compound a holding-period return to a yearly rate.

    Returns None below floor_days: annualizing a two-day trade multiplies its
    noise by ~180, and a -100% loss has no finite annualized form at all.
    """
    if days is None or days < floor_days or roi <= -1:
        return None
    try:
        return (1 + roi) ** (365.0 / days) - 1
    except (OverflowError, ValueError):
        return None


def xirr(flows: list[tuple[str, float]]) -> float | None:
    """Money-weighted annual return over dated cash flows (negative = paid in).

    Bisection rather than Newton: slower, but it cannot diverge, which matters
    on a flow series this irregular. Returns None when the flows don't bracket
    a root - typically because they never change sign.
    """
    dated = []
    for d, amt in flows:
        try:
            dated.append((dt.date.fromisoformat(d[:10]), amt))
        except (ValueError, TypeError):
            continue
    if len(dated) < 2:
        return None
    if not (any(a < 0 for _, a in dated) and any(a > 0 for _, a in dated)):
        return None

    t0 = min(d for d, _ in dated)

    def npv(rate: float) -> float:
        total = 0.0
        for d, amt in dated:
            years = (d - t0).days / 365.0
            total += amt / ((1 + rate) ** years)
        return total

    lo, hi = -0.9999, 100.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------
# Polymarket - public, unauthenticated
# --------------------------------------------------------------------------

def poly_get(path: str, params: dict) -> list[dict]:
    url = f"{POLY_BASE}{path}"
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    payload = r.json()
    return payload if isinstance(payload, list) else payload.get("data", [])


def poly_paged(path: str, wallet: str, page: int = 500, cap: int = 5000) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while offset < cap:
        batch = poly_get(path, {"user": wallet, "limit": page, "offset": offset})
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows


def fetch_polymarket(wallet: str) -> dict:
    open_raw = poly_paged("/positions", wallet)
    closed_raw = poly_paged("/closed-positions", wallet)

    # /activity carries the dated trade history the position endpoints lack:
    # it supplies each market's entry date and the cash flows the IRR needs.
    # YIELD rows are interest paid on idle USDC, not a trading result, so they
    # are counted separately and kept out of the return calculation.
    first_buy: dict[str, str] = {}
    flows: list[tuple[str, float]] = []
    yield_earned = 0.0
    try:
        for a in poly_paged("/activity", wallet):
            kind = (a.get("type") or "").upper()
            when = iso(a.get("timestamp"))
            usdc = num(a.get("usdcSize"))
            cid = a.get("conditionId")
            if kind == "YIELD":
                yield_earned += usdc
                continue
            if kind == "TRADE":
                if (a.get("side") or "").upper() == "BUY":
                    flows.append((when, -usdc))
                    if cid and (cid not in first_buy or when < first_buy[cid]):
                        first_buy[cid] = when
                else:
                    flows.append((when, usdc))
            elif kind in ("REDEEM", "CONVERSION"):
                flows.append((when, usdc))
    except requests.RequestException:
        pass

    positions = []
    for p in open_raw:
        slug = p.get("eventSlug") or p.get("slug") or ""
        cid = p.get("conditionId")
        cost = num(p.get("initialValue"))
        pnl = num(p.get("cashPnl"))
        opened = first_buy.get(cid)
        held = days_between(opened, None)
        roi = pnl / cost if cost else 0.0
        positions.append({
            "venue": "polymarket",
            "title": p.get("title"),
            "outcome": p.get("outcome"),
            "size": num(p.get("size")),
            "avg_price": num(p.get("avgPrice")),
            "cur_price": num(p.get("curPrice")),
            "cost_basis": cost,
            "current_value": num(p.get("currentValue")),
            "unrealized_pnl": pnl,
            "pct_pnl": num(p.get("percentPnl")),
            "fees": num(p.get("entryFeesUsdc")),
            "opened_at": opened,
            "days_held": held,
            "annualized": annualize(roi, held),
            "end_date": iso(p.get("endDate")),
            "redeemable": bool(p.get("redeemable")),
            "url": f"https://polymarket.com/event/{slug}" if slug else None,
        })

    closed = []
    for p in closed_raw:
        slug = p.get("eventSlug") or p.get("slug") or ""
        cid = p.get("conditionId")
        cost = num(p.get("totalBought")) * num(p.get("avgPrice"))
        realized = num(p.get("realizedPnl"))
        opened = first_buy.get(cid)
        closed_at = iso(p.get("timestamp") or p.get("endDate"))
        held = days_between(opened, closed_at)
        roi = realized / cost if cost else 0.0
        closed.append({
            "venue": "polymarket",
            "title": p.get("title"),
            "outcome": p.get("outcome"),
            "size": num(p.get("totalBought")),
            "avg_price": num(p.get("avgPrice")),
            "cost_basis": round(cost, 4),
            "realized_pnl": realized,
            "pct_pnl": round(roi * 100, 4),
            "opened_at": opened,
            "closed_at": closed_at,
            "days_held": held,
            "annualized": annualize(roi, held),
            "url": f"https://polymarket.com/event/{slug}" if slug else None,
        })

    # /value is the venue's own number for open position value - kept separately
    # so the dashboard can show it beside the sum we compute and expose any drift.
    reported_value = None
    try:
        v = poly_get("/value", {"user": wallet})
        if v:
            reported_value = num(v[0].get("value"))
    except requests.RequestException:
        pass

    return {
        "ok": True,
        "positions": positions,
        "closed": closed,
        "reported_open_value": reported_value,
        "cash": None,  # Polymarket USDC balance is not exposed on the public API
        "flows": flows,
        "yield_earned": round(yield_earned, 4),
    }


# --------------------------------------------------------------------------
# Kalshi - RSA-PSS signed
# --------------------------------------------------------------------------

def kalshi_headers(key_id: str, private_key, method: str, path: str) -> dict:
    """Sign timestamp + METHOD + path. The path must exclude the query string."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}{method.upper()}{path}".encode()
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
        "accept": "application/json",
    }


def kalshi_get(key_id: str, private_key, endpoint: str, params: dict | None = None) -> dict:
    path = f"{KALSHI_PREFIX}{endpoint}"
    r = SESSION.get(
        f"{KALSHI_BASE}{path}",
        params=params or {},
        headers=kalshi_headers(key_id, private_key, "GET", path),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def kalshi_paged(key_id, private_key, endpoint: str, field: str,
                 params: dict | None = None, cap: int = 5000) -> list[dict]:
    rows: list[dict] = []
    cursor = None
    while len(rows) < cap:
        q = dict(params or {})
        q["limit"] = 200
        if cursor:
            q["cursor"] = cursor
        payload = kalshi_get(key_id, private_key, endpoint, q)
        batch = payload.get(field) or []
        rows.extend(batch)
        cursor = payload.get("cursor")
        if not cursor or not batch:
            break
        time.sleep(0.25)  # stay clear of the rate limiter
    return rows


def kalshi_market_meta(key_id, private_key, tickers: list[str]) -> dict[str, dict]:
    """Current price and title per ticker, in chunks."""
    meta: dict[str, dict] = {}
    for i in range(0, len(tickers), 20):
        chunk = tickers[i:i + 20]
        try:
            payload = kalshi_get(key_id, private_key, "/markets",
                                 {"tickers": ",".join(chunk), "limit": 200})
            for m in payload.get("markets", []):
                meta[m.get("ticker")] = m
        except requests.RequestException:
            for t in chunk:  # fall back to one at a time
                try:
                    payload = kalshi_get(key_id, private_key, f"/markets/{t}")
                    m = payload.get("market") or {}
                    if m.get("ticker"):
                        meta[m["ticker"]] = m
                except requests.RequestException:
                    continue
        time.sleep(0.25)
    return meta


def fetch_kalshi(key_id: str, pem: str) -> dict:
    from cryptography.hazmat.primitives import serialization

    private_key = serialization.load_pem_private_key(pem.encode(), password=None)

    raw_positions = kalshi_paged(key_id, private_key, "/portfolio/positions",
                                 "market_positions", {"count_filter": "position"})
    raw_positions = [p for p in raw_positions
                     if num(p.get("position_fp") or p.get("position")) != 0]

    meta = kalshi_market_meta(key_id, private_key,
                              [p["ticker"] for p in raw_positions if p.get("ticker")])

    positions = []
    for p in raw_positions:
        ticker = p.get("ticker", "")
        m = meta.get(ticker, {})
        contracts = num(p.get("position_fp") or p.get("position"))
        is_yes = contracts > 0
        size = abs(contracts)

        price, basis = kalshi_price(m, is_yes)

        # market_exposure is the cost of the position EXCLUDING fees, while the
        # Kalshi app's "Cost" column includes them - and its "Total return" is
        # measured against that fee-inclusive cost. Add them back so both the
        # cost and the return line up with what the app shows.
        exposure = abs(num(p.get("market_exposure_dollars")))
        if not exposure and p.get("market_exposure") is not None:
            exposure = abs(num(p.get("market_exposure"))) / 100
        fees = num(p.get("fees_paid_dollars"))
        if not fees and p.get("fees_paid") is not None:
            fees = num(p.get("fees_paid")) / 100
        cost = exposure + fees

        if price is None:
            # Never invent a price: hold the position at cost and say so, rather
            # than reporting a -100% loss that is really a missing field.
            current_value, unrealized = cost, 0.0
        else:
            current_value = size * price
            unrealized = current_value - cost

        positions.append({
            "venue": "kalshi",
            "title": m.get("title") or ticker,
            "subtitle": m.get("yes_sub_title") or m.get("subtitle"),
            "ticker": ticker,
            "outcome": "Yes" if is_yes else "No",
            "size": size,
            "avg_price": round(cost / size, 4) if size else 0.0,
            "cur_price": round(price, 4) if price is not None else None,
            "price_basis": basis,
            "cost_basis": round(cost, 4),
            "current_value": round(current_value, 4),
            "unrealized_pnl": round(unrealized, 4),
            "pct_pnl": round(unrealized / cost * 100, 4) if cost else 0.0,
            "fees": round(fees, 4),
            "end_date": iso(m.get("close_time")),
            "redeemable": False,
            "url": f"https://kalshi.com/markets/{ticker}" if ticker else None,
        })

    # --- realized P&L, cash basis -------------------------------------------
    #
    # Settlements alone are not enough. A market exited by SELLING before it
    # resolved has a settlement payout of zero (or no settlement row at all),
    # so a settlement-only calculation books the whole cost as a loss and
    # silently drops positions traded out entirely.
    #
    # So this walks the fills instead: money out on buys, money in on sells,
    # plus any settlement payout. That is the same cash-in/cash-out framing as
    # the app's Total cost / Total payout / Total return columns, and it is
    # correct whether a market was sold out of, held to settlement, or both.

    fills = kalshi_paged(key_id, private_key, "/portfolio/fills", "fills")
    seen = {f.get("fill_id") for f in fills}
    try:
        for f in kalshi_paged(key_id, private_key, "/historical/fills", "fills"):
            if f.get("fill_id") not in seen:
                fills.append(f)
    except requests.RequestException:
        pass  # older fills unavailable; recent ones still count

    def fill_action(f: dict) -> str:
        a = f.get("action")
        if a in ("buy", "sell"):
            return a
        return "buy" if f.get("book_side") == "bid" else "sell"

    def fill_ticker(f: dict) -> str | None:
        return f.get("ticker") or f.get("market_ticker")

    # Which side of each market was actually held.
    #
    # Deliberately taken from the BUY fills only. On a sell, Kalshi reports
    # outcome_side as the side of the book the trade crossed, not the side held
    # - selling Yes is booked against No - so trusting it there prices the sale
    # at the complement, turning a 13c exit into 87c. Buys are reliable (every
    # cost basis reconciles against the app), so the buys fix the side and every
    # fill in that market is then priced from that side's field.
    flows: list[tuple[str, float]] = []
    sides: dict[str, bool] = {}
    for f in fills:
        t = fill_ticker(f)
        if t and fill_action(f) == "buy" and t not in sides:
            sides[t] = (f.get("outcome_side") or f.get("side")) == "yes"

    books: dict[str, dict] = {}
    for f in fills:
        t = fill_ticker(f)
        if not t:
            continue
        b = books.setdefault(t, {"cost": 0.0, "payout": 0.0, "bought": 0.0,
                                 "sold": 0.0, "proceeds": 0.0, "settled": 0.0,
                                 "fees": 0.0, "last": None, "first_buy": None,
                                 "side": None})
        count = num(f.get("count_fp") or f.get("count"))
        fee = num(f.get("fee_cost"))
        is_yes = sides.get(t, (f.get("outcome_side") or f.get("side")) == "yes")
        price = opt(f, "yes_price_dollars" if is_yes else "no_price_dollars",
                    "yes_price" if is_yes else "no_price") or 0.0

        when = iso(f.get("created_time") or f.get("ts"))
        b["side"] = "Yes" if is_yes else "No"
        if fill_action(f) == "buy":
            b["cost"] += count * price + fee
            b["bought"] += count
            if when and (b["first_buy"] is None or when < b["first_buy"]):
                b["first_buy"] = when
            flows.append((when, -(count * price + fee)))
        else:
            b["proceeds"] += count * price - fee
            b["payout"] += count * price - fee
            b["sold"] += count
            flows.append((when, count * price - fee))
        b["fees"] += fee
        if when and (b["last"] is None or when > b["last"]):
            b["last"] = when

    settled_at: dict[str, str] = {}
    for s in kalshi_paged(key_id, private_key, "/portfolio/settlements", "settlements"):
        t = s.get("ticker")
        if not t:
            continue
        b = books.setdefault(t, {"cost": 0.0, "payout": 0.0, "bought": 0.0,
                                 "sold": 0.0, "proceeds": 0.0, "settled": 0.0,
                                 "fees": 0.0, "last": None, "side": None})
        revenue = num(s.get("revenue")) / 100             # revenue is in cents
        b["payout"] += revenue
        b["settled"] += revenue
        if s.get("settled_time"):
            settled_at[t] = s["settled_time"]
        if revenue:
            flows.append((iso(s.get("settled_time")), revenue))

    still_open = {p["ticker"] for p in positions}
    closed_tickers = [t for t in books if t not in still_open]
    closed_meta = kalshi_market_meta(key_id, private_key, closed_tickers)

    for p in positions:                      # entry dates for the open side
        b = books.get(p["ticker"])
        if not b:
            continue
        p["opened_at"] = b["first_buy"]
        p["days_held"] = days_between(b["first_buy"], None)
        p["annualized"] = annualize(
            p["unrealized_pnl"] / p["cost_basis"] if p["cost_basis"] else 0.0,
            p["days_held"])

    closed = []
    for t in closed_tickers:
        b = books[t]
        if b["cost"] <= 0:
            continue
        realized = b["payout"] - b["cost"]
        closed_on = iso(settled_at.get(t) or b["last"])
        held = days_between(b["first_buy"], closed_on)
        closed.append({
            "venue": "kalshi",
            "title": (closed_meta.get(t) or {}).get("title") or t,
            "ticker": t,
            "outcome": b["side"] or "—",
            "size": round(b["bought"], 4),
            "avg_price": round(b["cost"] / b["bought"], 4) if b["bought"] else 0.0,
            "cost_basis": round(b["cost"], 4),
            "realized_pnl": round(realized, 4),
            "pct_pnl": round(realized / b["cost"] * 100, 4),
            "opened_at": b["first_buy"],
            "closed_at": closed_on,
            "days_held": held,
            "annualized": annualize(realized / b["cost"], held),
            "url": f"https://kalshi.com/markets/{t}",
            # Kept so a future mismatch against the app can be traced to the
            # sell leg or the settlement leg without re-deriving anything.
            "payout": round(b["payout"], 4),
            "sold": round(b["sold"], 4),
            "sale_proceeds": round(b["proceeds"], 4),
            "settlement_payout": round(b["settled"], 4),
            "fees": round(b["fees"], 4),
        })

    cash = None
    try:
        bal = kalshi_get(key_id, private_key, "/portfolio/balance")
        cash = num(bal.get("balance_dollars")) or num(bal.get("balance")) / 100
    except requests.RequestException:
        pass

    return {"ok": True, "positions": positions, "closed": closed,
            "reported_open_value": None, "cash": cash,
            "flows": flows, "yield_earned": 0.0}


# --------------------------------------------------------------------------
# assemble
# --------------------------------------------------------------------------

def totals(positions: list[dict], closed: list[dict],
           flows: list[tuple[str, float]] | None = None) -> dict:
    open_value = sum(p["current_value"] for p in positions)
    unrealized = sum(p["unrealized_pnl"] for p in positions)
    realized = sum(c["realized_pnl"] for c in closed)
    wins = [c for c in closed if c["realized_pnl"] > 0]
    staked = sum(p["cost_basis"] for p in positions) + \
        sum(c["cost_basis"] for c in closed)

    # Money-weighted return: every buy, sell and settlement at its own date,
    # with the open positions marked to market today as a closing inflow. This
    # is the figure comparable to other investments, because it accounts for
    # both timing and how much was at risk - unlike a simple sum of per-bet
    # percentages, which weights a $10 punt the same as a $100 one.
    irr = None
    if flows:
        series = list(flows)
        if open_value:
            series.append((TODAY.isoformat(), open_value))
        irr = xirr(series)

    held = [c["days_held"] for c in closed if c.get("days_held") is not None]

    return {
        "open_value": round(open_value, 2),
        "open_positions": len(positions),
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": round(realized, 2),
        "total_pnl": round(unrealized + realized, 2),
        "settled_markets": len(closed),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "best_win": round(max((c["realized_pnl"] for c in closed), default=0), 2),
        "worst_loss": round(min((c["realized_pnl"] for c in closed), default=0), 2),
        "staked": round(staked, 2),
        "roi": round((unrealized + realized) / staked, 6) if staked else None,
        "irr": round(irr, 6) if irr is not None else None,
        "median_days_held": sorted(held)[len(held) // 2] if held else None,
    }


def main() -> int:
    wallet = os.environ.get("POLYMARKET_WALLET", "").strip()
    key_id = os.environ.get("KALSHI_KEY_ID", "").strip()
    pem = os.environ.get("KALSHI_PRIVATE_KEY", "").strip()

    venues: dict[str, dict] = {}

    if wallet:
        try:
            venues["polymarket"] = fetch_polymarket(wallet)
            print(f"polymarket: {len(venues['polymarket']['positions'])} open, "
                  f"{len(venues['polymarket']['closed'])} settled")
        except Exception as exc:
            venues["polymarket"] = {"ok": False, "error": str(exc)[:200],
                                    "positions": [], "closed": [],
                                    "reported_open_value": None, "cash": None,
                                    "flows": [], "yield_earned": 0.0}
            print(f"polymarket: FAILED - {str(exc)[:200]}", file=sys.stderr)
    else:
        venues["polymarket"] = {"ok": False, "error": "POLYMARKET_WALLET not set",
                                "positions": [], "closed": [],
                                "reported_open_value": None, "cash": None,
                                "flows": [], "yield_earned": 0.0}

    if key_id and pem:
        try:
            venues["kalshi"] = fetch_kalshi(key_id, pem)
            print(f"kalshi: {len(venues['kalshi']['positions'])} open, "
                  f"{len(venues['kalshi']['closed'])} settled")
        except Exception as exc:
            # str(exc) on a requests error can include the URL but never the key,
            # which only ever travels in a header.
            venues["kalshi"] = {"ok": False, "error": str(exc)[:200],
                                "positions": [], "closed": [],
                                "reported_open_value": None, "cash": None,
                                "flows": [], "yield_earned": 0.0}
            print(f"kalshi: FAILED - {str(exc)[:200]}", file=sys.stderr)
    else:
        venues["kalshi"] = {"ok": False, "error": "no credentials configured",
                            "positions": [], "closed": [],
                            "reported_open_value": None, "cash": None,
                            "flows": [], "yield_earned": 0.0}
        print("kalshi: skipped (no credentials)")

    all_positions = [p for v in venues.values() for p in v["positions"]]
    all_closed = [c for v in venues.values() for c in v["closed"]]
    all_flows = [f for v in venues.values() for f in (v.get("flows") or [])]

    data = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "venues": {
            name: {
                "ok": v["ok"],
                "error": v.get("error"),
                "cash": v.get("cash"),
                "reported_open_value": v.get("reported_open_value"),
                "yield_earned": v.get("yield_earned"),
                **totals(v["positions"], v["closed"], v.get("flows")),
            }
            for name, v in venues.items()
        },
        "totals": totals(all_positions, all_closed, all_flows),
        "positions": sorted(all_positions, key=lambda p: -p["current_value"]),
        "closed": sorted(all_closed, key=lambda c: (c["closed_at"] or ""), reverse=True),
    }

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t = data["totals"]
    print(f"wrote {OUT.name}: open {t['open_value']:.2f}, "
          f"unrealized {t['unrealized_pnl']:+.2f}, realized {t['realized_pnl']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
