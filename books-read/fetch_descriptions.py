#!/usr/bin/env python3
"""Fetch a description (publisher blurb) for every book in books.csv into descriptions.json.

Runs in a GitHub Action whenever books.csv changes (a new StoryGraph export is uploaded). No API
key needed. Incremental: books already in descriptions.json are skipped, so a new export only
fetches the books added since the last one.

Sources, in order: Open Library by ISBN (edition, then work description), then Google Books by
ISBN, then Google Books by title + author for rows without a usable ISBN (StoryGraph puts an ASIN or
nothing in "ISBN/UID" for some audiobooks and ebooks). Open Library goes first because Google Books
throttles anonymous requests from GitHub's shared runner addresses hard (HTTP 429); after a few
consecutive throttles Google is skipped for the rest of the run and those books are retried next
time. Google Books' descriptions are HTML fragments; tags are stripped and paragraph breaks kept.

Robustness: every book is wrapped in a try/except (a failure becomes a "miss" with the reason, never
a crash), the JSON is saved every 10 books and on exit, and the run stops itself after TIME_BUDGET
seconds so the workflow always gets to its commit step. Set GOOGLE_BOOKS_API_KEY in the workflow
environment to lift Google's anonymous quota (optional; a free key from the Google Cloud console).

descriptions.json:
  { "updated": "...", "items": { <key>: { "desc", "src", "id", "title" } }, "misses": { <key>: "reason" } }
where <key> is the ISBN (digits only, X allowed) when the row has one, otherwise "title|first author"
lower-cased — the page derives the same key from its rows.
"""
import csv, html, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BOOKS = os.path.join(HERE, "books.csv")
OUT = os.path.join(HERE, "descriptions.json")
GB = "https://www.googleapis.com/books/v1/volumes"
OL = "https://openlibrary.org"
UA = {"User-Agent": "dashboards-books/1.0 (github.com/akaukora/dashboards)"}
SLEEP = 0.3
TIME_BUDGET = int(os.environ.get("TIME_BUDGET", "2400"))   # seconds; stop, save and exit 0 after this
GB_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "").strip()
GB_MAX_THROTTLES = 5                                        # consecutive 429/403 from Google → give up on it this run
gb_throttled = 0
gb_off = False


def isbn_of(row):
    raw = (row.get("ISBN/UID") or "").strip().replace("-", "").replace(" ", "").upper()
    return raw if re.fullmatch(r"\d{9}[\dX]|\d{13}", raw) else ""


def key_of(row):
    isbn = isbn_of(row)
    if isbn:
        return isbn
    author = (row.get("Authors") or "").split(",")[0].strip().lower()
    return f"{(row.get('Title') or '').strip().lower()}|{author}"


def clean(text):
    if not text:
        return ""
    if isinstance(text, dict):  # Open Library sometimes wraps it as {"type": "/type/text", "value": "..."}
        text = text.get("value", "")
    text = re.sub(r"<\s*(br|/p|/div)\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Open Library work descriptions often end with a "----------" + source line; cut it
    text = re.split(r"\n-{3,}", text)[0].strip()
    return text


class Throttled(Exception):
    pass


def get(url, retries=2):
    """GET JSON. None on 404 or after retries; raises Throttled on a persistent 429/403."""
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 403):
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise Throttled(f"HTTP {e.code}")
            if e.code >= 500 and attempt < retries:
                time.sleep(2)
                continue
            return None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            if attempt < retries:
                time.sleep(2)
                continue
            return None
    return None


def google(q):
    global gb_throttled, gb_off
    if gb_off:
        return None
    params = {"q": q, "maxResults": 3, "printType": "books"}
    if GB_KEY:
        params["key"] = GB_KEY
    try:
        d = get(f"{GB}?{urllib.parse.urlencode(params)}")
    except Throttled as e:
        gb_throttled += 1
        if gb_throttled >= GB_MAX_THROTTLES:
            gb_off = True
            print(f"  Google Books keeps answering {e} — skipping it for the rest of this run", file=sys.stderr)
        return None
    gb_throttled = 0
    for it in (d or {}).get("items") or []:
        v = it.get("volumeInfo") or {}
        desc = clean(v.get("description"))
        if len(desc) > 40:
            return {"desc": desc, "src": "google-books", "id": it.get("id"), "title": v.get("title", "")}
    return None


def openlibrary(isbn):
    try:
        ed = get(f"{OL}/isbn/{isbn}.json")
    except Throttled:
        return None
    if not ed:
        return None
    desc = clean(ed.get("description"))
    title = ed.get("title", "")
    for w in ed.get("works") or []:
        if len(desc) > 40:
            break
        try:
            work = get(f"{OL}{w['key']}.json") or {}
        except Throttled:
            work = {}
        desc = clean(work.get("description"))
        title = title or work.get("title", "")
    if len(desc) > 40:
        return {"desc": desc, "src": "open-library", "id": (ed.get("works") or [{}])[0].get("key", ed.get("key")), "title": title}
    return None


def lookup(row):
    isbn, title = isbn_of(row), (row.get("Title") or "").strip()
    author = (row.get("Authors") or "").split(",")[0].strip()
    if isbn:
        r = openlibrary(isbn)
        if r:
            return r, None
        time.sleep(SLEEP)
        r = google(f"isbn:{isbn}")
        if r:
            return r, None
        time.sleep(SLEEP)
    # last resort: title + author (also for ISBNs neither source knows)
    r = google(f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else ""))
    if r:
        return r, None
    if gb_off:
        return None, "Google Books throttled this run — will retry"
    return None, "no description found" + ("" if isbn else " (no ISBN)")


def main():
    with open(BOOKS, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    data = {"updated": None, "items": {}, "misses": {}}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            data.update(json.load(f))
    seen, todo = set(), []
    for r in rows:
        if not (r.get("Title") or "").strip():
            continue
        k = key_of(r)
        if k in seen:
            continue
        seen.add(k)
        if k not in data["items"]:
            todo.append((k, r))
    print(f"{len(seen)} books, {len(data['items'])} already described, {len(todo)} to fetch")
    data["items"] = {k: v for k, v in data["items"].items() if k in seen}
    data["misses"] = {k: v for k, v in data["misses"].items() if k in seen}

    def save():
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)

    added, done, t0 = 0, 0, time.time()
    for k, r in todo:
        if time.time() - t0 > TIME_BUDGET:
            print(f"time budget reached after {done} books — the rest is picked up on the next run", file=sys.stderr)
            break
        try:
            record, reason = lookup(r)
        except Exception as e:  # never let one book kill the run
            record, reason = None, f"error: {type(e).__name__}: {e}"
        if record:
            data["items"][k] = record
            data["misses"].pop(k, None)
            added += 1
        else:
            data["misses"][k] = reason
            print(f"  miss: {r.get('Title')} — {r.get('Authors')} — {reason}")
        done += 1
        if done % 10 == 0:
            data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            save()
            print(f"  … {done}/{len(todo)} ({added} found)", flush=True)
        time.sleep(SLEEP)
    if todo:
        data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save()
    left = len(todo) - done
    print(f"{added} added, {len(data['misses'])} unmatched{f', {left} not attempted yet' if left else ''} → {os.path.basename(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
