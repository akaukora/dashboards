import requests
from bs4 import BeautifulSoup
import feedparser
import csv
import time
import re

USERNAME = "farbeach"
RSS_URL = f"https://letterboxd.com/{USERNAME}/rss/"

TAGS = [
    "cinema", "streaming", "netflix", "finnkino", "amazon", "yle-areena",
    "mubi", "hbo-max", "disney-plus", "kino-engel", "kino-regina", "riviera",
    "savoy", "orion", "maxim", "imax", "atmos", "3d", "blu-ray", "vudu",
    "xbox", "tv", "airplane", "documentary", "short-film", "film-festival",
    "docpoint-festival", "espoo-cine", "night-visions-festival",
    "r-a-festival", "kids", "gilda", "skyshowtime"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PersonalDashboardBot/1.0)"}
OUTPUT_PATH = "films-watched/films.csv"


def extract_poster(entry):
    """Get poster URL from enclosure first, then fall back to <img> in description."""
    if getattr(entry, "enclosures", None):
        return entry.enclosures[0]["href"]
    description = entry.get("description", "") or ""
    m = re.search(r'<img src="(https://[^"]+)"', description)
    return m.group(1) if m else None


def fetch_poster_from_film_page(slug):
    """Fetch og:image from a Letterboxd film page as a last-resort poster source."""
    url = f"https://letterboxd.com/film/{slug}/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        og = soup.find("meta", property="og:image")
        return og["content"] if og else None
    except Exception:
        return None


def backfill_missing_posters(rows):
    """For any row missing poster_url, fetch it from the film page.
    Deduplicated by slug so each film is only fetched once."""
    seen_slugs = {}
    missing = [(i, r) for i, r in enumerate(rows) if not r.get("poster_url")]
    print(f"Backfilling posters for {len(missing)} rows...")
    for i, row in missing:
        slug = row["link"].strip().rstrip("/").split("/film/")[-1].split("/")[0]
        if slug not in seen_slugs:
            poster = fetch_poster_from_film_page(slug)
            seen_slugs[slug] = poster or ""
            time.sleep(0.5)
        rows[i]["poster_url"] = seen_slugs[slug]
    filled = sum(1 for _, r in missing if r.get("poster_url"))
    print(f"Backfill complete: {filled}/{len(missing)} posters found")
    return rows


def fetch_rss():
    feed = feedparser.parse(RSS_URL)
    entries = []
    for e in feed.entries:
        link = e.link
        slug = link.rstrip("/").split("/film/")[-1].split("/")[0]
        entries.append({
            "slug": slug,
            "title": e.title,
            "watched_date": getattr(e, "letterboxd_watcheddate", None),
            "film_year": getattr(e, "letterboxd_filmyear", None),
            "rating": getattr(e, "letterboxd_memberrating", None),
            "rewatch": getattr(e, "letterboxd_rewatch", None),
            "link": link,
            "poster_url": extract_poster(e),
            "tmdb_id": getattr(e, "tmdb_movieid", None),
        })
    return entries


def scrape_tag_pages():
    tag_map = {}
    for tag in TAGS:
        page = 1
        while True:
            url = (
                f"https://letterboxd.com/{USERNAME}/tag/{tag}/diary/"
                if page == 1
                else f"https://letterboxd.com/{USERNAME}/tag/{tag}/diary/page/{page}/"
            )
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("tr.diary-entry-row")
            if not rows:
                break
            for row in rows:
                item = row.select_one("[data-item-slug]")
                daylink = row.select_one("a.daydate")
                if not item or not daylink:
                    continue
                slug = item["data-item-slug"]
                m = re.search(r"/diary/for/(\d{4})/(\d{2})/(\d{2})/", daylink["href"])
                if not m:
                    continue
                date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                key = f"{slug}_{date}"
                tag_map.setdefault(key, []).append(tag)
            page += 1
            time.sleep(1)
    return tag_map


def load_existing(path=OUTPUT_PATH):
    existing = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                slug = row["link"].strip().rstrip("/").split("/film/")[-1].split("/")[0]
                key = f"{slug}_{row['watched_date']}"
                existing[key] = row
    except FileNotFoundError:
        pass
    return existing


def merge_and_write(entries, tag_map, outpath=OUTPUT_PATH):
    existing = load_existing(outpath)
    rss_keys = set()
    updated_rows = []
    fieldnames = ["watched_date", "title", "film_year", "rating", "rewatch", "tags", "link", "poster_url", "tmdb_id"]

    for e in entries:
        key = f"{e['slug']}_{e['watched_date']}"
        rss_keys.add(key)
        tags = tag_map.get(key, [])
        existing_poster = existing.get(key, {}).get("poster_url", "")
        updated_rows.append({
            "watched_date": e["watched_date"],
            "title": e["title"],
            "film_year": e["film_year"],
            "rating": e["rating"],
            "rewatch": e["rewatch"],
            "tags": ", ".join(tags),
            "link": e["link"],
            "poster_url": e["poster_url"] or existing_poster,
            "tmdb_id": e["tmdb_id"],
        })

    # preserve historical rows not covered by current RSS window
    for key, row in existing.items():
        if key not in rss_keys:
            updated_rows.append({
                "watched_date": row["watched_date"],
                "title": row["title"],
                "film_year": row["film_year"],
                "rating": row["rating"],
                "rewatch": row.get("rewatch", ""),
                "tags": row["tags"],
                "link": row["link"],
                "poster_url": row.get("poster_url", ""),
                "tmdb_id": row.get("tmdb_id", ""),
            })

    updated_rows.sort(key=lambda x: x["watched_date"] or "")

    # backfill any rows still missing a poster
    updated_rows = backfill_missing_posters(updated_rows)

    with open(outpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    print(f"Written {len(updated_rows)} rows to {outpath}")


if __name__ == "__main__":
    print("Fetching RSS feed...")
    entries = fetch_rss()
    print(f"Got {len(entries)} RSS entries")
    print("Scraping tag pages...")
    tag_map = scrape_tag_pages()
    print(f"Built tag map with {len(tag_map)} entries")
    merge_and_write(entries, tag_map)
