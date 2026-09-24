#!/usr/bin/env python3
"""Fetch a short synopsis for every film in films.csv from TMDB into descriptions.json.

Runs after scrape_letterboxd.py in the nightly GitHub Action. Incremental: films already in
descriptions.json are not fetched again, so the first run makes one request per film and later
runs only touch new diary entries. Needs a TMDB API key (free: themoviedb.org → Settings → API)
in the environment as TMDB_API_KEY; without one the script logs a warning and exits 0, so the
nightly job keeps working before the secret is added.

Matching: rows with a tmdb_id (the RSS feed carries it for newer entries) are looked up directly;
the rest are searched by title and release year. A search hit is accepted when its release year is
within a year of Letterboxd's; otherwise the film is recorded under "misses" and retried next run.

descriptions.json:
  { "source": "tmdb", "updated": "...", "items": { <key>: { "desc", "tmdb_id", "title", "year" } }, "misses": { <key>: "reason" } }
where <key> is the Letterboxd film slug (…/film/<slug>/), falling back to "title|year" — the page
derives the same key from its rows, so the CSV itself is not touched.
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FILMS = os.path.join(HERE, "films.csv")
OUT = os.path.join(HERE, "descriptions.json")
API = "https://api.themoviedb.org/3"
KEY = os.environ.get("TMDB_API_KEY", "").strip()
SLEEP = 0.06  # TMDB allows ~40-50 requests/second; be polite anyway


def key_of(row):
    m = re.search(r"/film/([^/]+)/?", row.get("link", "") or "")
    if m:
        return m.group(1).lower()
    return f"{(row.get('title') or '').strip().lower()}|{year_of(row) or ''}"


def year_of(row):
    y = (row.get("film_year") or "").strip()
    try:
        return int(float(y)) if y else None
    except ValueError:
        return None


def get(path, **params):
    params["api_key"] = KEY
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 or e.code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    return None


def lookup(row):
    """Return (record, reason). record is None when nothing acceptable was found."""
    title, year = (row.get("title") or "").strip(), year_of(row)
    tid = (row.get("tmdb_id") or "").strip()
    if tid:
        m = get(f"/movie/{int(float(tid))}", language="en-US")
        if m and m.get("overview"):
            return rec(m), None
    q = get("/search/movie", query=title, language="en-US", include_adult="false", **({"primary_release_year": year} if year else {}))
    hits = (q or {}).get("results") or []
    if not hits and year:  # year filter too strict (Letterboxd uses the earliest release year) — search without it
        q = get("/search/movie", query=title, language="en-US", include_adult="false")
        hits = (q or {}).get("results") or []
    for h in hits:
        hy = int(h["release_date"][:4]) if h.get("release_date") else None
        if year is None or hy is None or abs(hy - year) <= 1:
            if h.get("overview"):
                return rec(h), None
            return None, "match without overview"
    return None, "no TMDB match" if not hits else f"year mismatch (first hit {hits[0].get('release_date', '')[:4]})"


def rec(m):
    return {"desc": m["overview"].strip(), "tmdb_id": m["id"], "title": m.get("title", ""), "year": int(m["release_date"][:4]) if m.get("release_date") else None}


def main():
    if not KEY:
        print("TMDB_API_KEY not set — skipping descriptions (add it under Settings → Secrets → Actions).", file=sys.stderr)
        return 0
    with open(FILMS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data = {"source": "tmdb", "updated": None, "items": {}, "misses": {}}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            data.update(json.load(f))
    seen, todo = set(), []
    for r in rows:
        k = key_of(r)
        if k in seen or not (r.get("title") or "").strip():
            continue
        seen.add(k)
        if k not in data["items"]:
            todo.append((k, r))
    print(f"{len(seen)} films, {len(data['items'])} already described, {len(todo)} to fetch")
    added = 0
    for k, r in todo:
        record, reason = lookup(r)
        if record:
            data["items"][k] = record
            data["misses"].pop(k, None)
            added += 1
        else:
            data["misses"][k] = reason
            print(f"  miss: {r.get('title')} ({year_of(r)}) — {reason}")
        time.sleep(SLEEP)
    # drop items/misses for films no longer in the diary (e.g. deleted entries)
    data["items"] = {k: v for k, v in data["items"].items() if k in seen}
    data["misses"] = {k: v for k, v in data["misses"].items() if k in seen}
    if added or todo:
        data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{added} added, {len(data['misses'])} unmatched → {os.path.basename(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
