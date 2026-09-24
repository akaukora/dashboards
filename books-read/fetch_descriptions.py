#!/usr/bin/env python3
"""Fetch a description (publisher blurb) for every book in books.csv into descriptions.json.

Runs in a GitHub Action whenever books.csv changes (a new StoryGraph export is uploaded). No API
key needed. Incremental: books already in descriptions.json are skipped, so a new export only
fetches the books added since the last one.

Sources, in order: Google Books by ISBN, then Open Library by ISBN (work description), then Google
Books by title + author for rows without a usable ISBN (StoryGraph puts an ASIN or nothing in
"ISBN/UID" for some audiobooks and ebooks). Google Books' descriptions are HTML fragments; tags are
stripped and paragraph breaks kept.

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
SLEEP = 0.4  # Google Books throttles bursts from anonymous clients; ~1000 requests/day is plenty


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


def get(url):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 403) or e.code >= 500:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    return None


def google(q):
    d = get(f"{GB}?{urllib.parse.urlencode({'q': q, 'maxResults': 3, 'printType': 'books'})}")
    for it in (d or {}).get("items") or []:
        v = it.get("volumeInfo") or {}
        desc = clean(v.get("description"))
        if len(desc) > 40:
            return {"desc": desc, "src": "google-books", "id": it.get("id"), "title": v.get("title", "")}
    return None


def openlibrary(isbn):
    ed = get(f"{OL}/isbn/{isbn}.json")
    if not ed:
        return None
    desc = clean(ed.get("description"))
    title = ed.get("title", "")
    for w in ed.get("works") or []:
        if len(desc) > 40:
            break
        work = get(f"{OL}{w['key']}.json") or {}
        desc = clean(work.get("description"))
        title = title or work.get("title", "")
    if len(desc) > 40:
        return {"desc": desc, "src": "open-library", "id": (ed.get("works") or [{}])[0].get("key", ed.get("key")), "title": title}
    return None


def lookup(row):
    isbn, title = isbn_of(row), (row.get("Title") or "").strip()
    author = (row.get("Authors") or "").split(",")[0].strip()
    if isbn:
        r = google(f"isbn:{isbn}")
        if r:
            return r, None
        time.sleep(SLEEP)
        r = openlibrary(isbn)
        if r:
            return r, None
        time.sleep(SLEEP)
    # last resort: title + author (also for ISBNs neither source knows)
    r = google(f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else ""))
    if r:
        return r, None
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
    added = 0
    for k, r in todo:
        record, reason = lookup(r)
        if record:
            data["items"][k] = record
            data["misses"].pop(k, None)
            added += 1
        else:
            data["misses"][k] = reason
            print(f"  miss: {r.get('Title')} — {r.get('Authors')} — {reason}")
        time.sleep(SLEEP)
    data["items"] = {k: v for k, v in data["items"].items() if k in seen}
    data["misses"] = {k: v for k, v in data["misses"].items() if k in seen}
    if todo:
        data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{added} added, {len(data['misses'])} unmatched → {os.path.basename(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
