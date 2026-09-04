"""Letterboxd diary → films-watched/films.csv

Merges the RSS feed (last ~50 entries) into the existing CSV without destroying
what is already there. Rules of the merge:

  * a row is keyed by (film slug, watched date);
  * an RSS entry only ever ADDS or FILLS: a non-empty value from the feed replaces
    the stored value, an empty one never does (so hand-filled tags, reviews and
    posters survive a re-run);
  * the film title comes from <letterboxd:filmTitle>, never from the item title
    (which is "Title, 2026 - ★★★★★");
  * tags for each RSS entry are read from the entry's own diary page (the tag links
    on it), with the per-tag diary listings as a second source; if neither yields a
    tag the stored tags are kept, never blanked;
  * posters come from the RSS enclosure, else the film page's JSON-LD poster,
    else Letterboxd's poster endpoint — never og:image, which is a 16:9 still;
  * the previous CSV is copied to films.csv.bak before writing.
"""
import csv
import json
import re
import shutil
import sys
import time
from html import unescape

import feedparser
import requests
from bs4 import BeautifulSoup

USERNAME = "farbeach"
RSS_URL = f"https://letterboxd.com/{USERNAME}/rss/"
OUTPUT_PATH = "films-watched/films.csv"
# A browser-like User-Agent: Letterboxd answers bot-looking agents with 403 on some pages.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Tag slugs as they appear in letterboxd.com/<user>/tag/<slug>/diary/ and the
# name to store in the CSV (the dashboard's tag model uses the stored names).
TAGS = {
    "cinema": "cinema", "streaming": "streaming", "netflix": "netflix", "finnkino": "finnkino",
    "amazon": "amazon", "yle-areena": "yle areena", "mubi": "mubi", "hbo-max": "hbo max",
    "disney-plus": "disney plus", "skyshowtime": "skyshowtime", "kino-engel": "kino engel",
    "kino-regina": "kino regina", "riviera": "riviera", "savoy": "savoy", "orion": "orion",
    "maxim": "maxim", "gilda": "gilda", "imax": "imax", "atmos": "atmos", "3d": "3d",
    "blu-ray": "blu-ray", "vudu": "vudu", "xbox": "xbox", "tv": "tv", "airplane": "airplane",
    "documentary": "documentary", "short-film": "short film", "film-festival": "film festival",
    "docpoint-festival": "docpoint festival", "espoo-cine": "espoo ciné",
    "night-visions-festival": "night visions festival", "r-a-festival": "r&a festival", "kids": "kids",
}

# Column order of the CSV. The dashboard reads columns by name, so adding one is safe.
FIELDNAMES = ["title", "film_year", "watched_date", "rating", "tags", "review", "link", "poster_url", "rewatch", "tmdb_id"]

STILL_MARKERS = ("/sm/upload/", "-675-675-crop")   # 16:9 share images, not posters


# ---------------------------------------------------------------- helpers

def slug_of(link):
    """Film slug from a Letterboxd URL. Short links (boxd.it/…) have no slug, so the whole
    link is used as the key — otherwise every short link would collide on the same key."""
    link = (link or "").strip()
    if "/film/" not in link:
        return link.rstrip("/").rsplit("/", 1)[-1] if link else ""
    return link.rstrip("/").split("/film/")[-1].split("/")[0]


def resolve_short_link(link):
    """boxd.it/… → the full letterboxd.com/…/film/<slug>/ URL it redirects to (or the input)."""
    if "/film/" in link or "boxd.it" not in link:
        return link
    try:
        resp = requests.get(link, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and "/film/" in resp.url:
            return resp.url
    except requests.RequestException:
        pass
    return link


def is_poster(url):
    return bool(url) and not any(m in url for m in STILL_MARKERS)


def clean_title(item_title, film_title):
    """Prefer <letterboxd:filmTitle>; otherwise strip ', 2026 - ★★★★' from the item title."""
    if film_title:
        return film_title.strip()
    t = item_title or ""
    m = re.match(r"^(.*?),\s*\d{4}\s*-\s*[★½]*\s*$", t)
    return (m.group(1) if m else re.sub(r"\s*-\s*[★½]+\s*$", "", t)).strip()


def review_from_description(html):
    """The RSS description is: <p><img…/></p> <p>Watched on …</p> or <p>review paragraphs…</p>.
    Return the review text, or '' when the entry has no review."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    paras = []
    for p in soup.find_all("p"):
        if p.find("img"):
            continue
        text = p.get_text(" ", strip=True)
        if not text or re.match(r"^Watched on ", text):
            continue
        paras.append(text)
    return unescape("\n\n".join(paras)).strip()


def extract_poster(entry):
    """RSS enclosure first, then the <img> in the description (both are portrait posters)."""
    for enc in getattr(entry, "enclosures", None) or []:
        if is_poster(enc.get("href", "")):
            return enc["href"]
    m = re.search(r'<img src="(https://[^"]+)"', entry.get("description", "") or "")
    return m.group(1) if m and is_poster(m.group(1)) else ""


def fetch_poster_from_film_page(slug):
    """Poster (portrait) for a film: JSON-LD 'image' on the film page, else the poster endpoint.
    Never og:image — that is the 16:9 still."""
    try:
        resp = requests.get(f"https://letterboxd.com/film/{slug}/", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for script in soup.find_all("script", type="application/ld+json"):
                raw = script.string or ""
                raw = re.sub(r"^\s*/\*.*?\*/\s*", "", raw, flags=re.S)   # Letterboxd wraps it in a CDATA comment
                raw = re.sub(r"\s*/\*.*?\*/\s*$", "", raw, flags=re.S)
                try:
                    data = json.loads(raw)
                except ValueError:
                    continue
                img = data.get("image")
                if isinstance(img, str) and is_poster(img):
                    return img
        resp = requests.get(f"https://letterboxd.com/ajax/poster/film/{slug}/std/500x750/", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            img = soup.find("img")
            src = (img.get("src") or img.get("data-src") or "") if img else ""
            if is_poster(src) and "empty-poster" not in src:
                return src
    except requests.RequestException:
        pass
    return ""


def tag_name(slug_tag):
    """CSV name for a tag slug: the TAGS map, else the slug with hyphens as spaces."""
    return TAGS.get(slug_tag, slug_tag.replace("-", " "))


def fetch_entry_tags(link):
    """Tags of one diary entry, read from its own page: links of the form /<user>/tag/<slug>/…"""
    try:
        resp = requests.get(link, headers=HEADERS, timeout=15)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        print(f"  entry page {link} → HTTP {resp.status_code}")
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    found = []
    for a in soup.select(f'a[href*="/{USERNAME}/tag/"]'):
        m = re.search(rf"/{re.escape(USERNAME)}/tag/([^/]+)/", a.get("href", ""))
        if m and tag_name(m.group(1)) not in found:
            found.append(tag_name(m.group(1)))
    return found


# ---------------------------------------------------------------- sources

def fetch_rss():
    feed = feedparser.parse(RSS_URL)
    entries = []
    for e in feed.entries:
        link = e.link
        entries.append({
            "slug": slug_of(link),
            "title": clean_title(e.get("title"), getattr(e, "letterboxd_filmtitle", None)),
            "watched_date": getattr(e, "letterboxd_watcheddate", "") or "",
            "film_year": getattr(e, "letterboxd_filmyear", "") or "",
            "rating": getattr(e, "letterboxd_memberrating", "") or "",
            "rewatch": getattr(e, "letterboxd_rewatch", "") or "",
            "review": review_from_description(e.get("description", "")),
            "link": link,
            "poster_url": extract_poster(e),
            "tmdb_id": getattr(e, "tmdb_movieid", "") or "",
        })
    return entries


def scrape_tag_pages():
    """{ '<slug>_<YYYY-MM-DD>': [tag name, …] } from the per-tag diary pages."""
    tag_map = {}
    diagnosed = False
    for slug_tag, name in TAGS.items():
        page = 1
        while True:
            url = f"https://letterboxd.com/{USERNAME}/tag/{slug_tag}/diary/" + ("" if page == 1 else f"page/{page}/")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
            except requests.RequestException as exc:
                print(f"  {url} → {exc}")
                break
            if resp.status_code != 200:
                if page == 1:
                    print(f"  tag page {slug_tag}: HTTP {resp.status_code}")
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("tr.diary-entry-row")
            if not rows:
                if page == 1 and not diagnosed:
                    diagnosed = True
                    table = soup.select_one("table, section#diary-table, .diary-table")
                    print(f"  tag page {slug_tag}: 200 but no tr.diary-entry-row — markup sample: "
                          f"{(str(table)[:600] if table else resp.text[:300]).replace(chr(10), ' ')}")
                break
            for row in rows:
                item = row.select_one("[data-item-slug], [data-film-slug]")
                daylink = row.select_one("a.daydate, td.td-day a")
                if not item or not daylink:
                    continue
                slug = item.get("data-item-slug") or item.get("data-film-slug")
                m = re.search(r"/for/(\d{4})/(\d{2})/(\d{2})/", daylink.get("href", ""))
                if not m:
                    continue
                key = f"{slug}_{m.group(1)}-{m.group(2)}-{m.group(3)}"
                if name not in tag_map.setdefault(key, []):
                    tag_map[key].append(name)
            page += 1
            time.sleep(1)
    return tag_map


# ---------------------------------------------------------------- merge

def load_existing(path=OUTPUT_PATH):
    existing = {}
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                row = {k: (v or "").strip() for k, v in row.items() if k}
                row["title"] = clean_title(row.get("title", ""), None)          # repairs "Title, 2025 - ★★★" left by earlier runs
                existing[f"{slug_of(row.get('link', ''))}_{row.get('watched_date', '')}"] = row
    except FileNotFoundError:
        pass
    return existing


def merge_rows(entries, tag_map, existing, entry_tags=None):
    """Existing rows are the base; RSS values fill in or overwrite only when non-empty."""
    merged = dict(existing)
    entry_tags = entry_tags or {}
    for e in entries:
        key = f"{e['slug']}_{e['watched_date']}"
        row = dict(merged.get(key, {}))
        for field in ("title", "film_year", "watched_date", "rating", "rewatch", "review", "link", "tmdb_id"):
            if e.get(field):
                row[field] = str(e[field])
        if e["poster_url"] or not is_poster(row.get("poster_url", "")):
            row["poster_url"] = e["poster_url"] or ""
        tags = entry_tags.get(key) or tag_map.get(key)
        if tags:
            row["tags"] = ", ".join(tags)
        else:
            row.setdefault("tags", "")            # keep whatever the CSV had
        merged[key] = row
    rows = [{f: r.get(f, "") for f in FIELDNAMES} for r in merged.values()]
    rows.sort(key=lambda r: (r["watched_date"] == "", r["watched_date"], r["title"]))
    return rows


def backfill_missing_posters(rows):
    """Fill empty or still-type poster_url from the film page, one fetch per slug."""
    cache = {}
    todo = [r for r in rows if not is_poster(r["poster_url"])]
    print(f"Backfilling posters for {len(todo)} rows…")
    for r in todo:
        if r["link"] and "/film/" not in r["link"]:
            resolved = resolve_short_link(r["link"])
            if resolved != r["link"]:
                r["link"] = resolved                      # store the full URL so the row keys stay stable
                time.sleep(0.5)
        slug = slug_of(r["link"]) if "/film/" in r["link"] else ""
        if not slug:
            continue
        if slug not in cache:
            cache[slug] = fetch_poster_from_film_page(slug)
            time.sleep(0.5)
        if cache[slug]:
            r["poster_url"] = cache[slug]
    print(f"Backfill complete: {sum(1 for v in cache.values() if v)}/{len(cache)} films found")
    return rows


def write_csv(rows, path=OUTPUT_PATH):
    try:
        shutil.copyfile(path, path + ".bak")
    except FileNotFoundError:
        pass
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"Written {len(rows)} rows to {path} (previous version in {path}.bak)")


def main():
    existing = load_existing()
    print(f"Existing CSV: {len(existing)} rows")

    print("Fetching RSS feed…")
    entries = fetch_rss()
    print(f"Got {len(entries)} RSS entries")
    if not entries:
        sys.exit("RSS returned nothing — leaving the CSV untouched.")

    print("Reading tags from each entry's diary page…")
    entry_tags = {}
    for e in entries:
        key = f"{e['slug']}_{e['watched_date']}"
        tags = fetch_entry_tags(e["link"])
        if tags is not None:
            entry_tags[key] = tags
        time.sleep(0.5)
    print(f"  tags found for {sum(1 for v in entry_tags.values() if v)} of {len(entries)} entries")

    print("Scraping tag pages (second source)…")
    tag_map = scrape_tag_pages()
    print(f"  tag map covers {len(tag_map)} diary entries")
    if not tag_map and not any(entry_tags.values()):
        print("WARNING — no tags could be read from Letterboxd at all; stored tags are kept, new entries get none.")

    rows = merge_rows(entries, tag_map, existing, entry_tags)
    rows = backfill_missing_posters(rows)

    # sanity report before writing
    n_tags = sum(1 for r in rows if r["tags"])
    n_rev = sum(1 for r in rows if r["review"])
    n_poster = sum(1 for r in rows if is_poster(r["poster_url"]))
    lost_tags = [r["title"] for k, r0 in existing.items() if r0.get("tags")
                 for r in [next((x for x in rows if f"{slug_of(x['link'])}_{x['watched_date']}" == k), None)] if r and not r["tags"]]
    print(f"Rows: {len(rows)} · with tags: {n_tags} · with review: {n_rev} · with poster: {n_poster}")
    if lost_tags:
        print(f"WARNING — these rows would lose their tags: {', '.join(lost_tags[:10])}")
    write_csv(rows)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:            # make the Actions log show the real reason
        import traceback
        traceback.print_exc()
        sys.exit(1)
