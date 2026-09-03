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


def fetch_rss():
    feed = feedparser.parse(RSS_URL)
    entries = []
    for e in feed.entries:
        link = e.link
        slug = link.rstrip("/").split("/film/")[-1].split("/")[0]
        # poster image comes as an enclosure in the RSS item
        poster_url = e.enclosures[0]["href"] if getattr(e, "enclosures", None) else None
        # tmdb:movieId is exposed by feedparser as tmdb_movieid
        tmdb_id = getattr(e, "tmdb_movieid", None)
        entries.append({
            "slug": slug,
            "title": e.title,
            "watched_date": getattr(e, "letterboxd_watcheddate", None),
            "film_year": getattr(e, "letterboxd_filmyear", None),
            "rating": getattr(e, "letterboxd_memberrating", None),
            "rewatch": getattr(e, "letterboxd_rewatch", None),
            "link": link,
            "poster_url": poster_url,
            "tmdb_id": tmdb_id,
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
                slug = row["link"].rstrip("/").split("/film/")[-1].split("/")[0]
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
        updated_rows.append({
            "watched_date": e["watched_date"],
            "title": e["title"],
            "film_year": e["film_year"],
            "rating": e["rating"],
            "rewatch": e["rewatch"],
            "tags": ", ".join(tags),
            "link": e["link"],
            "poster_url": e["poster_url"],
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
