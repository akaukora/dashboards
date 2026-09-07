#!/usr/bin/env python3
"""Pull a Last.fm user's scrobble history into music/scrobbles.csv, incrementally.

First run: backfills the whole history in 30-day windows (user.getRecentTracks with from/to),
oldest first, checkpointing as it goes; an interrupted run keeps what it fetched and continues
next time. Later runs: only the windows newer than the newest scrobble on file.
Also rewrites music/artists.csv (one row per artist: plays, first/last played, plays per year),
which is what the dashboard loads first; the raw scrobbles are there for drill-downs.

Environment:  LASTFM_API_KEY (required)   LASTFM_USER (default: akaukora)
Options:      --full        ignore the existing file's newest timestamp and re-fetch everything
              --max-pages N safety cap on API pages per run (default 3000 = 600 000 scrobbles)
              --data DIR    folder for the CSVs (default: the script's folder)

The API key is not a login: it only reads what is public on the profile. Keep it in a
repository secret anyway so it is not sitting in the workflow file.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://ws.audioscrobbler.com/2.0/"
FIELDS = ["uts", "datetime_utc", "artist", "album", "track", "loved"]
PAGE_SIZE = 200
CHECKPOINT_EVERY = 25          # pages; a long backfill survives a hiccup without starting over
PAUSE = 0.25                   # seconds between calls — Last.fm asks for well under 5 requests/s


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------- API
def get_page(session, key, user, page, since_uts, until_uts=None):
    """One page of user.getRecentTracks, newest first. Retries on rate limits and 5xx."""
    params = {"method": "user.getrecenttracks", "user": user, "api_key": key, "format": "json",
              "limit": PAGE_SIZE, "page": page, "extended": 1}
    if since_uts:
        params["from"] = since_uts + 1          # `from` is inclusive; we already have since_uts
    if until_uts:
        params["to"] = until_uts                # freeze the window so pages don't shift while scrobbles arrive mid-run
    for attempt in range(6):
        try:
            r = session.get(API, params=params, timeout=60)
        except requests.RequestException as e:
            log(f"  page {page}: {e}; retrying"); time.sleep(2 ** attempt); continue
        if r.status_code == 200:
            data = r.json()
            if "error" in data:                  # Last.fm reports errors inside a 200 as well
                raise RuntimeError(f"Last.fm error {data['error']}: {data.get('message')}")
            return data["recenttracks"]
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** attempt
            log(f"  page {page}: HTTP {r.status_code}; waiting {wait}s"); time.sleep(wait); continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    raise RuntimeError(f"page {page}: gave up after repeated errors")


def rows_from(tracks):
    """Turn the API's track objects into CSV rows; the 'now playing' entry has no date and is skipped."""
    out = []
    for t in tracks:
        if "date" not in t:                      # nowplaying
            continue
        uts = int(t["date"]["uts"])
        artist = t["artist"]
        out.append({
            "uts": uts,
            "datetime_utc": datetime.fromtimestamp(uts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "artist": (artist.get("name") if isinstance(artist, dict) else str(artist)).strip(),
            "album": (t.get("album") or {}).get("#text", "").strip(),
            "track": t.get("name", "").strip(),
            "loved": "1" if str(t.get("loved", "0")) == "1" else "",
        })
    return out


# ----------------------------------------------------------------------------- files
def read_scrobbles(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["uts"] = int(r["uts"])
    return rows


def write_scrobbles(path: Path, rows):
    rows.sort(key=lambda r: (r["uts"], r["artist"], r["track"]))
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    tmp.replace(path)


CORRECTIONS_FILE = "corrections.csv"


def apply_corrections(rows, path: Path):
    """Rewrite artist / album / track for rows matching corrections.csv (case-insensitive artist + track;
    match_track "*" = every track of that artist; blank target columns keep the old value). Last.fm itself
    cannot be edited through the API, so this is where scrobbles logged under a wrong artist get fixed."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as f:
        rules = [r for r in csv.DictReader(f) if (r.get("match_artist") or "").strip()]
    exact = {(r["match_artist"].strip().lower(), (r.get("match_track") or "").strip().lower()): r for r in rules if (r.get("match_track") or "").strip() not in ("", "*")}
    whole = {r["match_artist"].strip().lower(): r for r in rules if (r.get("match_track") or "").strip() in ("", "*")}
    n = 0
    for row in rows:
        rule = exact.get((row["artist"].lower(), row["track"].lower())) or whole.get(row["artist"].lower())
        if not rule:
            continue
        for col in ("artist", "album", "track"):
            if (rule.get(col) or "").strip():
                row[col] = rule[col].strip()
        n += 1
    return n


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["uts"], r["artist"].lower(), r["track"].lower())
        if k in seen:
            continue
        seen.add(k); out.append(r)
    return out


def write_artists(path: Path, rows):
    """artist, plays, first_played, last_played, loved_tracks, years — years as '2019:120|2020:33'."""
    by = defaultdict(list)
    for r in rows:
        by[r["artist"]].append(r)
    years_all = sorted({datetime.fromtimestamp(r["uts"], timezone.utc).year for r in rows})
    out = []
    for artist, rs in by.items():
        rs.sort(key=lambda r: r["uts"])
        per_year = defaultdict(int)
        for r in rs:
            per_year[datetime.fromtimestamp(r["uts"], timezone.utc).year] += 1
        out.append({
            "artist": artist,
            "plays": len(rs),
            "first_played": rs[0]["datetime_utc"][:10],
            "last_played": rs[-1]["datetime_utc"][:10],
            "tracks": len({r["track"].lower() for r in rs}),
            "loved_tracks": len({r["track"].lower() for r in rs if r["loved"]}),
            "years": "|".join(f"{y}:{per_year[y]}" for y in years_all if per_year[y]),
        })
    out.sort(key=lambda a: (-a["plays"], a["artist"].lower()))
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["artist", "plays", "first_played", "last_played", "tracks", "loved_tracks", "years"])
        w.writeheader(); w.writerows(out)
    tmp.replace(path)
    return out


# ----------------------------------------------------------------------------- windows
# Last.fm's deep page numbers (page 300 of 530…) are unreliable — some pages 500 persistently and
# the numbering shifts as scrobbles arrive. So the history is fetched in short time windows
# (from/to), oldest first, a handful of pages each. Every finished window is a checkpoint, so an
# interrupted run keeps what it got and the next run resumes from the newest scrobble on file.
WINDOW = 30 * 86400            # seconds per window; ~500 scrobbles/month → 3 pages
STATE_FILE = "fetch_state.json"


def registered_at(session, key, user):
    """The account's registration time — where a full backfill starts. Falls back to 2002 (Last.fm's launch)."""
    try:
        r = session.get(API, params={"method": "user.getinfo", "user": user, "api_key": key, "format": "json"}, timeout=30)
        return int(r.json()["user"]["registered"]["unixtime"])
    except Exception as e:                       # noqa: BLE001
        log(f"  user.getinfo failed ({e}); starting from 2002"); return 1009843200


def fetch_window(session, key, user, t0, t1):
    """All scrobbles with t0 <= uts <= t1. Pages are few here, so page numbers are safe."""
    rows, page, total_pages = [], 1, None
    while True:
        chunk = get_page(session, key, user, page, t0 - 1, t1)   # get_page adds 1 to `from`
        if total_pages is None:
            total_pages = int(chunk.get("@attr", {}).get("totalPages", 1))
        tracks = chunk.get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
        rows.extend(rows_from(tracks))
        if page >= total_pages:
            return rows
        page += 1
        time.sleep(PAUSE)


def load_state(path: Path):
    try:
        import json
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:                            # noqa: BLE001
        return {}


def save_state(path: Path, state):
    import json
    path.write_text(json.dumps(state, indent=1))


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--max-pages", type=int, default=3000, help="(kept for compatibility; windows make it moot)")
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()

    key = os.environ.get("LASTFM_API_KEY")
    user = os.environ.get("LASTFM_USER", "akaukora")
    if not key:
        sys.exit("LASTFM_API_KEY is not set")
    data = Path(args.data)
    scrobbles_path, artists_path, state_path = data / "scrobbles.csv", data / "artists.csv", data / STATE_FILE

    session = requests.Session()
    session.headers["User-Agent"] = "dashboards-lastfm-fetch/2.0 (github.com/akaukora/dashboards)"

    existing = [] if args.full else read_scrobbles(scrobbles_path)
    state = {} if args.full else load_state(state_path)
    until = int(time.time())
    # windows still to fetch: any that failed last time, then everything newer than what we have
    todo = [tuple(w) for w in state.get("failed", [])]
    start = (max(r["uts"] for r in existing) + 1) if existing else registered_at(session, key, user)
    t = start
    while t <= until:
        todo.append((t, min(t + WINDOW - 1, until))); t += WINDOW
    log(f"{user}: {len(existing)} scrobbles on file" + (f", newest {datetime.fromtimestamp(start - 1, timezone.utc):%Y-%m-%d %H:%M} UTC" if existing else "") + f" — {len(todo)} windows to fetch" + (f" ({len(state.get('failed', []))} retried from last run)" if state.get("failed") else ""))

    rows, failed, got = existing, [], 0
    for i, (t0, t1) in enumerate(todo, 1):
        try:
            new = fetch_window(session, key, user, t0, t1)
        except Exception as e:                   # noqa: BLE001 — keep going; the window is retried next run
            log(f"  window {datetime.fromtimestamp(t0, timezone.utc):%Y-%m-%d} – {datetime.fromtimestamp(t1, timezone.utc):%Y-%m-%d} FAILED: {e}")
            failed.append([t0, t1]); continue
        if new:
            rows = dedupe(rows + new); got += len(new)
        if i % 12 == 0 or new and len(new) > 150:
            write_scrobbles(scrobbles_path, rows); save_state(state_path, {"failed": failed, "checkpoint": t1})
            log(f"  {datetime.fromtimestamp(t1, timezone.utc):%Y-%m-%d}: {len(rows)} scrobbles so far ({i}/{len(todo)} windows)")
        time.sleep(PAUSE)

    if failed:                                   # one more try for the stragglers before giving up on them for this run
        still = []
        for t0, t1 in failed:
            time.sleep(5)
            try:
                new = fetch_window(session, key, user, t0, t1); rows = dedupe(rows + new); got += len(new)
            except Exception as e:               # noqa: BLE001
                log(f"  retry {datetime.fromtimestamp(t0, timezone.utc):%Y-%m-%d} failed again: {e}"); still.append([t0, t1])
        failed = still

    fixed = apply_corrections(rows, data / CORRECTIONS_FILE)
    if fixed:
        log(f"  corrections.csv: {fixed} scrobbles re-credited")
    write_scrobbles(scrobbles_path, rows)
    artists = write_artists(artists_path, rows)
    save_state(state_path, {"failed": failed, "completed_through": until if not failed else None, "run": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    log(f"done: +{got} scrobbles → {len(rows)} total, {len(artists)} artists; "
        f"{rows[0]['datetime_utc'][:10] if rows else '—'} – {rows[-1]['datetime_utc'][:10] if rows else '—'}")
    if failed:
        log(f"WARNING: {len(failed)} window(s) could not be fetched and are queued for the next run: " + ", ".join(f"{datetime.fromtimestamp(a, timezone.utc):%Y-%m-%d}" for a, _ in failed))
        sys.exit(2)                              # non-zero so the run shows as failed, but the data written above is committed by the workflow


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:                            # noqa: BLE001 — full traceback in the Actions log
        import traceback; traceback.print_exc(); sys.exit(1)
