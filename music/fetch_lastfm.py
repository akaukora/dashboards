#!/usr/bin/env python3
"""Pull a Last.fm user's scrobble history into music/scrobbles.csv, incrementally.

First run: backfills the whole history (user.getRecentTracks, 200 rows a page, oldest kept).
Later runs: asks only for scrobbles newer than the newest one already in the file and appends.
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


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--max-pages", type=int, default=3000)
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()

    key = os.environ.get("LASTFM_API_KEY")
    user = os.environ.get("LASTFM_USER", "akaukora")
    if not key:
        sys.exit("LASTFM_API_KEY is not set")
    data = Path(args.data)
    scrobbles_path, artists_path = data / "scrobbles.csv", data / "artists.csv"

    existing = read_scrobbles(scrobbles_path)
    since = 0 if args.full or not existing else max(r["uts"] for r in existing)
    log(f"{user}: {len(existing)} scrobbles on file" + (f", newest {datetime.fromtimestamp(since, timezone.utc):%Y-%m-%d %H:%M} UTC" if since else "") + (" — full re-fetch" if args.full else ""))

    session = requests.Session()
    session.headers["User-Agent"] = "dashboards-lastfm-fetch/1.0 (github.com/akaukora/dashboards)"
    new, page, total_pages = [], 1, None
    until = int(time.time())
    while True:
        chunk = get_page(session, key, user, page, since, until)
        attr = chunk.get("@attr", {})
        if total_pages is None:
            total_pages = int(attr.get("totalPages", 1)); total = int(attr.get("total", 0))
            log(f"  {total} new scrobbles on {total_pages} pages")
            if total == 0:
                break
        tracks = chunk.get("track", [])
        if isinstance(tracks, dict):             # a single track comes back as an object, not a list
            tracks = [tracks]
        new.extend(rows_from(tracks))
        if page % CHECKPOINT_EVERY == 0:
            write_scrobbles(scrobbles_path, dedupe(existing + new)); log(f"  page {page}/{total_pages} · checkpoint {len(existing) + len(new)} rows")
        if page >= total_pages or page >= args.max_pages:
            break
        page += 1
        time.sleep(PAUSE)

    before = len(existing)
    rows = dedupe(new if (args.full and new) else existing + new)
    write_scrobbles(scrobbles_path, rows)
    artists = write_artists(artists_path, rows)
    added = len(rows) - before
    log(f"done: +{added} scrobbles → {len(rows)} total, {len(artists)} artists; "
        f"{rows[0]['datetime_utc'][:10] if rows else '—'} – {rows[-1]['datetime_utc'][:10] if rows else '—'}")
    if page >= args.max_pages and total_pages and page < total_pages:
        log(f"NOTE: stopped at the --max-pages cap ({args.max_pages}); run again to continue")


if __name__ == "__main__":
    main()
