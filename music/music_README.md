# Music — Last.fm scrobbles

A dashboard of the Last.fm listening history plus the pipeline that keeps its data fresh. Live
at `https://akaukora.github.io/dashboards/music/` once this folder is in the `dashboards`
repository as `music/`.

## Files

- `index.html` — the dashboard. Reads `scrobbles.csv` from the same folder on every visit
  (`?src=<url>` overrides it for testing) and does everything in the browser: about a second
  to parse 100 000+ rows.

- `fetch_lastfm.py` — pulls the scrobble history of `LASTFM_USER` (default `akaukora`) through
  the Last.fm API into `scrobbles.csv`, and rebuilds `artists.csv`. Incremental: each run asks
  only for scrobbles newer than the newest one already on file.
- `update-lastfm.yml` — GitHub Actions workflow. Goes in `.github/workflows/`, not in this
  folder. Runs daily at 03:17 UTC and on demand (Actions → *Update Last.fm* → *Run workflow*,
  where a *full* checkbox re-fetches everything).
- `scrobbles.csv` — one row per scrobble: `uts, datetime_utc, artist, album, track, loved`.
  Sorted oldest first. `loved` is `1` for tracks marked loved on Last.fm, blank otherwise.
- `artists.csv` — one row per artist, most played first: `artist, plays, first_played,
  last_played, tracks, loved_tracks, years` where `years` is `2019:120|2020:33|…`. A compact
  summary for other uses (the dashboard computes the same from the raw scrobbles).

## The dashboard

The centrepiece is **Forgotten favourites**: artists you played at least *N* times (20 / 50 /
100 / 250) from at least *M* different tracks (any / 5 / 10 / 15 — the old Tableau definition was
50 plays and 15 tracks) but haven't heard for 6 / 12 / 24 / 36 months, sortable by plays, by
silence, or by both (plays × log of the silence). Each row has plays-per-year bars over your whole history, the
peak year, a recency pill, a link to the artist in your Last.fm library and a plays button that
filters the whole dashboard to that artist. The **Rediscovered** toggle shows the mirror image:
favourites you came back to in the last twelve months after a gap of at least the chosen length
(three or more plays since). With a year or month filter on, "favourite" means an artist you
played *N*+ times *in that period* — so 2016's favourites who have since gone quiet — while the
silence is still measured to today.

**When did I last listen to each artist?** is the bubble chart from the Tableau version: every
artist with `BUBBLE_MIN_PLAYS`+ plays, x = the last time you played them, y = plays (log scale by
default, Linear toggle), bubble size = distinct tracks. Forgotten favourites are bright green,
favourites still heard a muted green, everything else grey; the big bubbles far from the right
edge are the ones to rediscover. Hover for the artist, click to filter.

Around it: five KPI tiles (scrobbles, this year vs the same point last year with a background
sparkline, favourites and how many are silent, new artists this year, last scrobble);
scrobbles per year with a Columns / Lines / Per artist toggle (Per artist = scrobbles ÷ distinct
artists that year — the old "average times listened per artist"); the month heatmap; **Top artists** with a
recency pill each (becomes *Top tracks* when an artist is selected); a **listening clock**
(weekday × hour, Helsinki time); **New artists per year** with the share of the year's scrobbles
that went to artists heard for the first time (becomes *Albums* for a selected artist); recent
scrobbles with ♥ for loved tracks; and a table view capped at 1 000 rows with search.

Cross-filtering works as on the film page: year buttons, heatmap cells and artist names all add
filters, shown in the sticky bar with an × each, and kept in the URL hash (`#y=2016&a=Sigur%20R%C3%B3s`).
The favourites controls (silence, minimum plays, sort, tab) are remembered in the browser.

`MILESTONES` at the top of the script draws thin dashed lines with a label on the time charts —
it starts with 11 Jan 2009, the switch from owned music in iTunes to streaming; add moves, jobs
or anything else as `{ date: "YYYY-MM-DD", label: "…" }`.

Other config constants sit next to it: `TOP_COUNT`, `RECENT_COUNT`, `FAV_PAGE`, `TABLE_MAX`,
`BUBBLE_MIN_PLAYS`, `DEFAULTS` for the favourites controls, `RECENCY` (months → pill colour), and
`localDate()` which converts UTC to Helsinki time without the slow `Intl` path (EET/EEST rules).

## One-time setup

1. Create a Last.fm API account at <https://www.last.fm/api/account/create> (any application
   name; callback URL can stay empty). Copy the **API key** — the shared secret is not needed.
2. In the `dashboards` repository: **Settings → Secrets and variables → Actions → New repository
   secret**, name `LASTFM_API_KEY`, value = the key.
3. Add `music/fetch_lastfm.py` and `.github/workflows/update-lastfm.yml` to the repository.
4. **Actions → Update Last.fm → Run workflow.** The first run backfills the whole history:
   200 scrobbles per API call at four calls a second, so 100 000 scrobbles take about two to
   three minutes plus a checkpoint commit-free write every 25 pages. The log ends with a line
   like `done: +98 412 scrobbles → 98 412 total, 2 310 artists; 2008-03-02 – 2026-09-06`.
5. From then on the daily run appends what is new and commits only when something changed.

## Notes

- The API key only reads public data (the same as anyone sees on last.fm/user/akaukora); it is
  kept as a secret so it is not lying in the workflow file. If the Last.fm profile is set to hide
  recent listening, the API returns nothing — the *Hide recent listening information* setting in
  Last.fm privacy must be off.
- Timestamps are UTC in the file; the dashboard converts them to Helsinki time (`localDate()` in the script) for the heatmaps and the listening clock.
- Last.fm occasionally returns the same scrobble twice across pages; rows are de-duplicated on
  (timestamp, artist, track). The fetch window is frozen at the run's start time so pages don't
  shift when a scrobble arrives mid-run.
- Size: roughly 70 bytes per scrobble, so 100 000 scrobbles ≈ 7 MB — fine for GitHub (soft
  limit 50 MB per file) and for the browser, which parses it in well under a second.
- `python music/fetch_lastfm.py --full` re-fetches everything (also from the workflow's *full*
  checkbox); `--max-pages N` caps a run; `--data DIR` points at another folder for testing.
