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
- `scrobbles.csv` — one row per play: `uts, datetime_utc, artist, album, track, loved, source`.
  Sorted oldest first. `loved` is `1` for tracks marked loved on Last.fm, blank otherwise (kept
  in the data, not shown on the page). `source` is blank for Last.fm scrobbles and `spotify` for
  the rows merged from the Spotify export (below).
- `spotify_backfill.csv` + `spotify_backfill.py` — the Spotify side. Spotify's *Extended streaming
  history* export (Account → Privacy settings → Download your data; one `Streaming_History_Audio_<year>.json`
  per year, arrives by email after a few days) showed that the Last.fm scrobbler was silent for most
  of 2014, 2016 and 2018 and patchy in 2012–2019: about 27,700 Spotify plays of 30 s+ have no
  scrobble. Last.fm's API refuses scrobbles older than two weeks, so the history is repaired here
  instead: `python music/spotify_backfill.py my_spotify_data.zip` writes every play of 30 s+ to
  `spotify_backfill.csv` (start time = Spotify's end timestamp minus `ms_played`; podcasts and
  audiobooks skipped; Spotify's own double rows collapsed), and `fetch_lastfm.py` merges that file
  into `scrobbles.csv` on every run — `merge_backfill()` drops the previously merged rows and
  re-derives them, so the CSV and the rule are the single source of truth. A Spotify play is taken as
  already scrobbled when Last.fm has the same artist and track within ±10 minutes, or *any* track of
  that artist within ±60 s of the play's start (Last.fm auto-corrects titles — "Levels - Radio Edit"
  becomes "Levels", "(feat. …)" is dropped — so titles are compared with brackets and " - …" suffixes
  removed, and the artist-level rule catches the rest). The run log reports `N Spotify plays added
  that Last.fm never got (M already scrobbled)`. To refresh after a newer export, re-run the script
  and commit the new CSV; nothing else changes. The export on file covers 28 May 2009 – 2 Jul 2024.
- `corrections.csv` — fixes applied to the scrobbles on every write, because Last.fm's own data can't
  be edited through the API. Columns `match_artist, match_track, artist, album, track, note`: a row
  matches scrobbles by artist + track (case-insensitive; `match_track` `*` or blank means every track
  of that artist) and overwrites the non-blank target columns. It starts with the 218 iTunes-era
  scrobbles logged under the non-existent artist "Disney", re-credited to their performers (Phil
  Collins, Lea Salonga, Samuel E. Wright, …) and film soundtrack albums; where a song has a film
  version and a pop single (Circle of Life, A Whole New World, Beauty and the Beast…) the film
  version was assumed and the note says so. Add rows for any other cleanup; run the workflow to
  apply them (the file is rewritten in full on every run).
- `artists.csv` — one row per artist, most played first: `artist, plays, first_played,
  last_played, tracks, loved_tracks, years` where `years` is `2019:120|2020:33|…`. A compact
  summary for other uses (the dashboard computes the same from the raw scrobbles).

## The dashboard

What counts as a favorite is a dashboard-level setting, in the pinned bar under the years, and
reads as a sentence: *Favorite artist = 50+ plays, from 10+ tracks played 3+ times each; forgotten
after 1 yr.* Each number is a button group (plays 20 / 50 / 100 / 250; tracks any / 5 / 10 / 15;
plays per track 1 / 2 / 3 / 5; silence 6 mo / 1 / 2 / 3 yrs). The "played 3+ times each" clause is
what keeps an artist with three heavily played songs and twenty one-offs out of the list — Antti
Tuisku (240 plays, 28 tracks, only 3 of them played 3+ times) is not a favorite, Tapio Rautavaara
(446 plays, 15 tracks with 3+ plays) is. With the defaults there are 237 favorite artists. The
same row switches between **Artist** and **Track** favorites (tracks: 10 / 15 / 25 / 50 plays).

The centerpiece is **Forgotten favorites**: the favorites you haven't heard for the chosen
silence, sortable by plays, by silence, or by both (plays × log of the silence). In Track mode the card — and the bubble
chart below it — show individual tracks, and the plays button filters to the track's artist. Each row has plays-per-year bars over your whole history, the
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

The KPI row is the executive summary, in the order of the sections below it: scrobbles; this
year vs the same point last year (background sparkline: cumulative by month); the last 7 days as
a percentage change against the 7 days before, with weekly totals of the last 12 weeks as the
background line; concentration — the share of the period's plays that went to its top 10 artists,
shaded to that share, with the Herfindahl–Hirschman index of artist shares and its inverse, the
number of equally-played artists it corresponds to; new artists out of all artists heard in the period, shaded; forgotten
favorites out of all favorites, gray for the forgotten share.

The page is organized in three collapsible groups. **Rediscover** holds the favorites list and the
bubble chart. **Discover** holds *New artists per year* (its tooltip also says how many of that
year's new artists are favorites today); **Favorites discovered per year** — of today's favorites,
how many were heard for the first time each year (blue) and how many crossed the play threshold that
year (green), with the running total; its *Growth lines* mode is the earlier view — one
cumulative-plays line per favorite artist over the whole history on a log scale, the selected
artist highlighted in green against the muted rest, with the favorite threshold drawn as a dashed
line so you can see when an artist crossed from occasional listen to favorite (Taylor Swift: first
heard 2008, crossed 50 plays in 2019); and **Newest favorites** — today's favorites (artists or
tracks, following the Artist/Track switch) by the date you first heard them, newest first, each row
showing the first play and how long it took to reach the threshold. With a year filter it becomes
"favorites first heard in 2016", i.e. that year's discoveries that stuck; with an artist selected
(the *Find an artist* box, or a click on any name) the card becomes that artist's story — "Taylor
Swift · favorite since 12 Jul 2018: first heard 3 Aug 2008; crossed the 50-play line 9.9 years
later; 2,150 plays now" — or, for a non-favorite, how far short it is and why; the per-year chart's
note says the same in years; the first year of the
history holds everything already known when scrobbling began, and the note says so. **Listening**
holds the rest:
scrobbles per year with a Columns / Lines / Per artist toggle (Per artist = scrobbles ÷ distinct
artists that year — the old "average times listened per artist"); one heatmap card with a **Months / Time of day**
toggle (scrobbles per month, or weekday × hour in Helsinki time); **Top artists** and **Top tracks** side by side,
for the current selection or — via the Selection / 7 days / 30 days / Last *N* weeks control — for
a recent window regardless of year filters, so "what was that thing I played a lot last week" has
an answer; in window mode the pill marks artists heard for the first time in that window (with an
artist selected the two cards become that artist's *Albums* and *Top tracks*); **New artists per year** with the share of the year's scrobbles that
went to artists heard for the first time (for a selected artist: their plays by month of the year,
a seasonal profile); **Now vs before** — paired bars for scrobbles, artists, tracks, albums and
days with music, the last 7 or 30 days against the period before, or this year to date against
the same days last year (green = now, gray = before, with the % change); recent scrobbles; a
**Listening fingerprint** radar comparing the focus year with
your all-time average on consistency (share of days with listening), discovery rate, week-to-week
variance, concentration (share of plays to the top 10 artists) and replay rate — Last.fm's own
chart compares to a global average, which we don't have; and a table view capped at 1 000 rows.

Cross-filtering works as on the film page: year buttons (click several to combine them —
`#y=2012,2013`; *Last 12 months* is a rolling window, `#l=1`), heatmap cells and artist names all add filters. On desktop the year buttons and the active-filter bar stay pinned to the top of the
window while scrolling (on phones they scroll away, to save space); the bar turns green whenever a
filter is on, so a filtered view is hard to mistake for the whole; filters show with an × each, and are kept in the URL hash (`#y=2016&a=Sigur%20R%C3%B3s`).
The pinned top bar also has a **Find an artist** box: two letters bring suggestions (most played
first), Enter or a pick filters the page to that artist — the way to reach anyone outside the top
lists, including in the favorites-growth chart, where a selected non-favorite still gets its line.
The favorite definition, the kids' setting, the sort, the chart toggles and the three collapsible
groups are remembered in the browser. Each favorites row has a small × that hides that artist or track from
the favorites lists (browser-only, undone with the "hidden · show again" link) — handy for the
kids' playlist era. In *Recent scrobbles*, favorites carry a tag, and a favorite heard again after
the chosen silence is highlighted green with "back after …". Artist names that differ only by case or a leading "The"
("Killers" / "The Killers") are merged, the most-played spelling winning, and so are track titles
that differ only by case. Collaboration credits
written as "Taylor Swift, Post Malone" or "A feat. B" are counted under the first-named artist —
but only when that artist also appears alone with `CREDIT_MIN_PLAYS`+ plays, so "Earth, Wind &
Fire" stays one act; "&", "and" and "x" are never treated as separators because they are almost
always band names (Amadou & Mariam, Of Monsters and Men). `KEEP_TOGETHER` lists comma names that
are single acts. The full credit is kept for the table and the recent list ("Fortnight (with Post
Malone)"), and the footer reports how many scrobbles were re-credited. Set `SPLIT_CREDITS = false`
to turn this off.

**Kids' songs.** `KIDS_TRACKS` in the page holds the kids' playlist as `[artist, track, liked]`
(64 songs, from the Kids playlist spreadsheet). Songs are matched to scrobbles by artist and title
with bracketed parts and " - …" suffixes ignored (56 of 64 match; the footer lists the ones that
don't, mostly titles spelled differently by the service). The *Kids' songs* control in the
definition row has three states: include everything, hide the kids' songs you don't like (the
`liked = false` ones), or hide all kids' songs. Hiding rebuilds the data, so it applies everywhere —
favorites, tops, charts and KPIs — and the subtitle says when it's on. With unliked songs hidden,
Ikuinen vappu and Sata salamaa leave the top tracks while Rosvo-Roope and Señorita stay.

A one-paragraph intro under the title says what Last.fm is for visitors who don't know it and
links to the drop-in viewer, as does the green *Try it with your own data →* button in the nav. The
footer shows only the latest scrobble's time and when the page loaded; the notes about where the
data comes from sit behind an *About the data* toggle (the same pattern on the film and book pages).

`MILESTONES` at the top of the script draws thin dashed lines with a label on the time charts —
it starts with 11 Jan 2009, the switch from owned music in iTunes to streaming; add moves, jobs
or anything else as `{ date: "YYYY-MM-DD", label: "…" }`.

Other config constants sit next to it: `TOP_COUNT`, `RECENT_COUNT`, `FAV_PAGE`, `TABLE_MAX`,
`BUBBLE_MIN_PLAYS`, `DEFAULTS` for the favorites controls, `RECENCY` (months → pill color), and
`localDate()` which converts UTC to Helsinki time without the slow `Intl` path (EET/EEST rules).

## The drop-in viewer

`music-viewer/` is a version of this page for other people's data: it accepts Last.fm exporter files
(Last.fm to CSV, lastfmstats.com, ghan.nl), Spotify's extended streaming history JSON and Apple
Music's play-activity CSV, parses them in the browser and keeps them in IndexedDB. It is generated
from this page by `music-viewer/make_music_viewer.py` — regenerate it after editing `index.html`
here. See `music-viewer/README.md`.

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

- With the Spotify backfill the dashboard reads about 134,000 plays instead of 106,700, and the
  favorites list grows from 237 to 270 — Avicii, for one, becomes a forgotten favorite whose peak
  year (2018) was almost empty in Last.fm alone. The page still says "scrobbles" for all of them.
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
