# Music — Last.fm scrobbles

A dashboard of the Last.fm listening history plus the pipeline that keeps its data fresh. Live
at `https://akaukora.github.io/dashboards/music/` once this folder is in the `dashboards`
repository as `music/`.

## Files

- `index.html` — the dashboard. Reads `scrobbles.csv` from the same folder on every visit
  (`?src=<url>` overrides it for testing) and does everything in the browser: about a second
  to parse 100 000+ rows.

- `fetch_lastfm.py` — pulls the scrobble history of `LASTFM_USER` (default `akaukora`) through
  the Last.fm API into `scrobbles.csv`, and rebuilds `artists.csv`. Works in 30-day time
  windows rather than deep page numbers (Last.fm's page 300-of-500 requests fail unpredictably),
  checkpoints as it goes, and on later runs asks only for windows newer than the newest scrobble
  on file. `fetch_state.json` (written next to the CSVs) remembers windows that failed so they
  are retried on the next run.
- `update-lastfm.yml` — GitHub Actions workflow. Goes in `.github/workflows/`, not in this
  folder. Runs daily at 03:17 UTC and on demand (Actions → *Update Last.fm* → *Run workflow*,
  where a *full* checkbox re-fetches everything).
- `scrobbles.csv` — one row per scrobble: `uts, datetime_utc, artist, album, track, loved`.
  Sorted oldest first. `loved` is `1` for tracks marked loved on Last.fm, blank otherwise.
- `artists.csv` — one row per artist, most played first: `artist, plays, first_played,
  last_played, tracks, loved_tracks, years` where `years` is `2019:120|2020:33|…`. A compact
  summary for other uses (the dashboard computes the same from the raw scrobbles).

## The dashboard

The centerpiece is **Forgotten favorites**: artists you played at least *N* times (20 / 50 /
100 / 250) from at least *M* different tracks (any / 5 / 10 / 15 — the old Tableau definition was
50 plays and 15 tracks) but haven't heard for 6 / 12 / 24 / 36 months, sortable by plays, by
silence, or by both (plays × log of the silence). An **Artists / Tracks** toggle switches the
whole card — and the bubble chart below it — to individual tracks (threshold 10 / 15 / 25 / 50
plays), where the plays button still filters to the track's artist. Each row has plays-per-year bars over your whole history, the
peak year, a recency pill, a link to the artist in your Last.fm library and a plays button that
filters the whole dashboard to that artist. The **Rediscovered** toggle shows the mirror image:
favorites you came back to in the last twelve months after a gap of at least the chosen length
(three or more plays since). With a year or month filter on, "favorite" means an artist you
played *N*+ times *in that period* — so 2016's favorites who have since gone quiet — while the
silence is still measured to today.

**When did I last listen to each artist?** is the bubble chart from the Tableau version: every
artist with `BUBBLE_MIN_PLAYS`+ plays, x = the last time you played them, y = plays (log scale by
default, Linear toggle), bubble size = distinct tracks (plays, in Tracks mode). Forgotten
favorites are green outlines with no fill, favorites still heard solid green, everything else
faint gray; the big bubbles far from the right
edge are the ones to rediscover. Hover for the artist, click to filter.

Around it: six KPI tiles (scrobbles; this year vs the same point last year with a background
sparkline; favorite artists heard this year out of all favorites, shaded to that share;
forgotten favorites out of all favorites, gray for the forgotten share, with how many are silent
3+ years; new artists this year, shaded to their share of the year's artists; the last 7 days vs the week before, with a 12-week sparkline and the last scrobble);
scrobbles per year with a Columns / Lines / Per artist toggle (Per artist = scrobbles ÷ distinct
artists that year — the old "average times listened per artist"); one heatmap card with a **Months / Time of day**
toggle (scrobbles per month, or weekday × hour in Helsinki time); **Top artists** with a recency
pill each (becomes *Top tracks* when an artist is selected); **New artists per year** with the share of the year's scrobbles
that went to artists heard for the first time (becomes *Albums* for a selected artist); recent
scrobbles with ♥ for loved tracks; **This week vs last week** — Last.fm-style rings for scrobbles,
tracks, albums and artists in the last 7 (or 30) days against the period before, the tick at the
bottom meaning "the same as before"; a **Listening fingerprint** radar comparing the focus year with
your all-time average on consistency (share of days with listening), discovery rate, week-to-week
variance, concentration (share of plays to the top 10 artists) and replay rate — Last.fm's own
chart compares to a global average, which we don't have; and a table view capped at 1 000 rows.

Cross-filtering works as on the film page: year buttons (click several to combine them —
`#y=2012,2013`), heatmap cells and artist names all add filters. On desktop the year buttons and the active-filter bar stay pinned to the top of the
window while scrolling (on phones they scroll away, to save space); filters show with an × each, and kept in the URL hash (`#y=2016&a=Sigur%20R%C3%B3s`).
The **Artists / Tracks** switch sits in the pinned top bar because it drives two cards. The
favorites controls (silence, minimum plays, sort, tab), the chart toggles and the two collapsible
groups (**Rediscover** — favorites and the bubble chart; **Listening** — everything else) are
remembered in the browser. Each favorites row has a small × that hides that artist or track from
the favorites lists (browser-only, undone with the "hidden · show again" link) — handy for the
kids' playlist era. In *Recent scrobbles*, favorites carry a tag, and a favorite heard again after
the chosen silence is highlighted green with "back after …". Artist names that differ only by case or a leading "The"
("Killers" / "The Killers") are merged, the most-played spelling winning. Collaboration credits
written as "Taylor Swift, Post Malone" or "A feat. B" are counted under the first-named artist —
but only when that artist also appears alone with `CREDIT_MIN_PLAYS`+ plays, so "Earth, Wind &
Fire" stays one act; "&", "and" and "x" are never treated as separators because they are almost
always band names (Amadou & Mariam, Of Monsters and Men). `KEEP_TOGETHER` lists comma names that
are single acts. The full credit is kept for the table and the recent list ("Fortnight (with Post
Malone)"), and the footer reports how many scrobbles were re-credited. Set `SPLIT_CREDITS = false`
to turn this off.

A one-paragraph intro under the title says what Last.fm is for visitors who don't know it.

`MILESTONES` at the top of the script draws thin dashed lines with a label on the time charts —
it starts with 11 Jan 2009, the switch from owned music in iTunes to streaming; add moves, jobs
or anything else as `{ date: "YYYY-MM-DD", label: "…" }`.

Other config constants sit next to it: `TOP_COUNT`, `RECENT_COUNT`, `FAV_PAGE`, `TABLE_MAX`,
`BUBBLE_MIN_PLAYS`, `DEFAULTS` for the favorites controls, `RECENCY` (months → pill color), and
`localDate()` which converts UTC to Helsinki time without the slow `Intl` path (EET/EEST rules).

## One-time setup

1. Create a Last.fm API account at <https://www.last.fm/api/account/create> (any application
   name; callback URL can stay empty). Copy the **API key** — the shared secret is not needed.
2. In the `dashboards` repository: **Settings → Secrets and variables → Actions → New repository
   secret**, name `LASTFM_API_KEY`, value = the key.
3. Add `music/fetch_lastfm.py` and `.github/workflows/update-lastfm.yml` to the repository.
4. **Actions → Update Last.fm → Run workflow.** The first run backfills the whole history in
   30-day windows, oldest first — roughly 700 API calls for 100 000 scrobbles, five to ten
   minutes. The log ends with a line like
   `done: +98 412 scrobbles → 98 412 total, 2 310 artists; 2008-03-02 – 2026-09-06`.
   If Last.fm refuses some windows even after retries, the run is marked failed (exit 2) but
   everything else is committed anyway, the failed windows are listed in the log and queued in
   `fetch_state.json`, and the next run fetches them first. Just run it again.
5. From then on the daily run appends what is new and commits only when something changed.

## Notes

- The API key only reads public data (the same as anyone sees on last.fm/user/akaukora); it is
  kept as a secret so it is not lying in the workflow file. If the Last.fm profile is set to hide
  recent listening, the API returns nothing — the *Hide recent listening information* setting in
  Last.fm privacy must be off.
- Timestamps are UTC in the file; the dashboard converts them to Helsinki time (`localDate()` in the script) for the heatmaps and the listening clock.
- Last.fm occasionally returns the same scrobble twice; rows are de-duplicated on (timestamp,
  artist, track). The run's end time is frozen at its start so a scrobble arriving mid-run lands
  in the next run, not in a shifted page.
- The workflow's commit step runs even when the fetch fails, so a partial backfill is never lost.
  The "Node.js 20 is deprecated" annotation is GitHub's notice about `actions/checkout` and
  `actions/setup-python`, not about this script; it is harmless.
- Size: roughly 70 bytes per scrobble, so 100 000 scrobbles ≈ 7 MB — fine for GitHub (soft
  limit 50 MB per file) and for the browser, which parses it in well under a second.
- `python music/fetch_lastfm.py --full` re-fetches everything (also from the workflow's *full*
  checkbox); `--max-pages N` caps a run; `--data DIR` points at another folder for testing.
