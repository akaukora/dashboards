#!/usr/bin/env python3
"""
Pull Finnkino showtimes into shows.json for the watchlist dashboard.

The Vista/OCAPI endpoint needs a bearer token. Finnkino embeds a short-lived
application token in its own page HTML (initialData.api.authToken), so we lift
a fresh one on every run rather than storing a secret.
"""
import json, re, sys, datetime as dt, urllib.request, urllib.error, pathlib

SITES = {                      # capital region; add ids to taste
    "1111": "Tennispalatsi",
    "1100": "Kinopalatsi",
    "1103": "Maxim",
    "1162": "Itis",
    "1157": "Omena",
}
DAYS = 21
API = "https://digital-api.finnkino.fi/WSVistaWebClient/ocapi/v1/showtimes/by-business-date/"
UA = "Mozilla/5.0 (compatible; personal-watchlist/1.0)"
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "shows.json")
STATUS = OUT.with_name("status.json")


def write_status(ok, note, **extra):
    """Written on every run, success or failure, so the page can show staleness."""
    STATUS.write_text(json.dumps({
        "lastRun": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "ok": ok, "note": note, **extra}, ensure_ascii=False, indent=1), "utf-8")


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def get_token():
    html = get("https://www.finnkino.fi/")
    m = re.search(r'"authToken"\s*:\s*"(eyJ[A-Za-z0-9_.\-]+)"', html)
    if not m:
        m = re.search(r'(eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})', html)
    if not m:
        raise RuntimeError("could not find auth token in finnkino.fi HTML")
    return m.group(1)


def txt(node):
    """Vista wraps display strings as {text, translations}."""
    if not node:
        return ""
    if isinstance(node, str):
        return node
    return (node.get("text") or "").strip()


def en(node):
    if not node:
        return ""
    for t in node.get("translations") or []:
        if (t.get("languageTag") or "").startswith("en"):
            return (t.get("text") or "").strip()
    return ""


def main():
    token = get_token()
    hdrs = {"Accept": "application/json", "Authorization": "Bearer " + token,
            "Referer": "https://www.finnkino.fi/", "Origin": "https://www.finnkino.fi"}
    q = "&".join("siteIds=" + s for s in SITES)

    films, screens, attrs, ratings, shows = {}, {}, {}, {}, []
    failed = []
    today = dt.date.today()
    for i in range(DAYS):
        day = (today + dt.timedelta(days=i)).isoformat()
        try:
            data = json.loads(get(f"{API}{day}?{q}", hdrs))
        except Exception as e:
            failed.append(f"{day}: {type(e).__name__} {e}")
            print(f"  {day}: {e}", file=sys.stderr)
            continue
        rel = data.get("relatedData") or {}
        for f in rel.get("films") or []:
            films.setdefault(f["id"], {
                "title": txt(f.get("title")),
                "titleEn": en(f.get("title")),
                "synopsis": txt(f.get("shortSynopsis")) or txt(f.get("synopsis"))[:400],
                "runtime": f.get("runtimeInMinutes"),
                "released": f.get("releaseDate"),
                "genres": f.get("genreIds") or [],
                "rating": f.get("censorRatingId"),
                "distributor": f.get("distributorName"),
            })
        for s in rel.get("screens") or []:
            screens[s["id"]] = txt(s.get("name"))
        for a in rel.get("attributes") or []:
            attrs[a["id"]] = {"name": txt(a.get("name")), "short": txt(a.get("shortName")),
                              "desc": txt(a.get("description"))}
        for g in rel.get("genres") or []:
            attrs.setdefault("g" + g["id"], {"name": en(g.get("name")) or txt(g.get("name"))})
        for c in rel.get("censorRatings") or []:
            ratings[c["id"]] = txt(c.get("classification"))

        for sh in data.get("showtimes") or []:
            sch = sh.get("schedule") or {}
            shows.append({
                "id": sh["id"],
                "film": sh.get("filmId"),
                "site": sh.get("siteId"),
                "screen": screens.get(sh.get("screenId"), sh.get("screenId")),
                "start": (sch.get("startsAt") or "")[:16],
                "end": (sch.get("endsAt") or "")[:16],
                "soldOut": bool(sh.get("isSoldOut")),
                "attrs": sh.get("attributeIds") or [],
            })
        print(f"  {day}: {len(data.get('showtimes') or [])} showtimes", file=sys.stderr)

    genres = {("g" + k[1:] if k.startswith("g") else k): v for k, v in attrs.items() if k.startswith("g")}

    # carry forward the date each film first appeared, so "newly announced" works
    prev = {}
    if OUT.exists():
        try:
            prev = (json.loads(OUT.read_text("utf-8")).get("films") or {})
        except Exception:
            pass
    stamp = today.isoformat()
    for fid, f in films.items():
        f["firstSeen"] = (prev.get(fid) or {}).get("firstSeen", stamp)

    if not shows:
        raise RuntimeError("no showtimes returned for any day — keeping the previous "
                           "shows.json; the API shape or token may have changed")

    out = {"generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
           "days": DAYS, "sites": SITES, "films": films, "shows": shows,
           "attrs": {k: v for k, v in attrs.items() if not k.startswith("g")},
           "genres": {k[1:]: v["name"] for k, v in attrs.items() if k.startswith("g")},
           "ratings": ratings}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    last = max((s["start"] for s in shows), default="")
    write_status(True, "ok", showtimes=len(shows), films=len(films),
                 daysWithData=DAYS - len(failed), furthestShow=last[:10],
                 failedDays=failed)
    print(f"{len(shows)} showtimes / {len(films)} films -> {OUT} "
          f"({OUT.stat().st_size/1024:.0f} kB)", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                       # token gone, shape changed, site down
        write_status(False, f"{type(e).__name__}: {e}")
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
