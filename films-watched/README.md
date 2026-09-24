# Letterboxd diary dashboard

A single self-contained `index.html` that reads `films.csv` from the same folder of the
repository on every page load and renders the dashboard in the browser. No build step, no backend, nothing to keep running.

## Publish on GitHub Pages (one-time, ~3 minutes)

1. On GitHub, create a new **public** repository, e.g. `letterboxd-dashboard`.
   Tick "Add a README" so the repo isn't empty, or skip it and upload below.
2. Upload `index.html` to the root of the repository
   (**Add file → Upload files**, drag it in, commit to `main`).
3. Open **Settings → Pages**. Under *Build and deployment* choose
   **Source: Deploy from a branch**, branch **main**, folder **/ (root)**, then **Save**.
4. After about a minute the page is live at
   `https://<your-username>.github.io/letterboxd-dashboard/`.
   That is the link to share.

Every later edit is: change `index.html`, commit, wait ~1 minute. GitHub keeps the
history, so a bad edit is one revert away. If you would rather not use GitHub,
dragging the same file onto Netlify Drop or Cloudflare Pages works identically.

## Editing

Everything lives in `index.html`:

- `DATA_URL` near the top of the `<script>` is the raw-GitHub link to `films.csv`. If the file
  moves, this is the only line to change.
- `RECENT_COUNT` is how many posters *Recent watches* shows; `RECENT_RATED` how many
  dots *Recent ratings* shows (unlabelled; hover for the film).
- `TAG_LABELS` renames viewing tags for display only (currently `cinema` → `theater`); the
  data keeps the original tag, so the table search matches both spellings.
- Tag roles: every film gets exactly one **source** (its service or venue), so nothing is
  double-counted. Every theater visit — whether tagged `cinema`, `finnkino`, `kino regina`
  or another venue in `THEATER_VENUES` — is the single source **theater**; the venue name is
  kept as detail in the table, tooltips and the theater row's hover. For home viewing the
  specific service is the source and the umbrella `streaming` tag only stands in when no
  service was tagged ("streaming, unspecified"); `SECONDARY_TAGS` (documentary, film festival, imax, 3d, atmos, kids) describe the film
  or screening and get their own Tags button row (`MIN_TAG_CHIP` films needed) instead of
  appearing as sources; `TAG_ALIASES` folds the named festivals (espoo ciné, r&a, docpoint,
  night visions) into the generic `film festival` tag. Failsafes for forgotten umbrella tags:
  a service tag alone (`netflix`) counts as home viewing, a venue alone (`finnkino`, `gilda`) as a
  theater visit, and `IMPLIES_THEATER` (imax, film festival and the festival names; 3d and atmos are not in it, since they happen at home too)
  makes a film tagged only with those count as a theater visit too.
- The *Watched in <year>* tile carries a faint background sparkline: cumulative films by month
  for the current year (green) against the previous year (gray).
- *Films per year* has a Columns / Lines toggle (remembered in the browser). Lines shows
  cumulative films by month with one line per year: the chosen (or current) year in green,
  the others in grays, older = darker; clicking a line filters to that year.
- *Ratings by service* has a Bars / Mekko toggle (remembered in the browser). Bars: one 100%-stacked
  row per service, theater first, average and count at the row end. Mekko: a Marimekko where column
  width is the service's share of rated films and height the rating mix, so block area = films;
  hover a column for the breakdown, click to filter. Small services lose their labels on narrow
  screens but keep the hover/tap.
- `MIN_SOURCE_CHIP` is how many films a tag needs to get its own Source button;
  `MIN_TAG_FILMS` how many rated films it needs for a row in *Ratings by service*.
- `RATING_MEANING` and `RATING_COLORS` are the five-step scale (5 must see … 1 skip) and
  its colours: greens for 4–5, steel blue for 3, and two receding grays for 2 and 1. Every chart that
  colours by rating reads from here.
- Colours are CSS variables in `:root` at the top of `<style>`.
- Each card is a small block in `render()`; the Chart.js configs are plain objects,
  so adding a chart is copy-paste-adjust.
- Filtering is cross-filtering: the Year and Source buttons, a click on a year bar, a rating
  column, a decade bar, a heatmap month, a service row or a Tags button all add a filter, and every card
  re-renders against the combined selection (a chart never filters itself — it highlights the
  chosen item and dims the rest). Active filters show in a bar that sticks to the top of the
  viewport while you scroll, with an × each and a Clear all; the state is
  kept in the URL hash (`#y=2024&s=netflix&r=4&t=documentary`) so a filtered view can be shared. The filter
  model is the `F` object and `filtered(skip)` near the top of the state section.
- For a quick local test with a different data file, open the page with
  `?src=path/to/file.csv` appended (relative to the page or a full URL).

Charts come from Chart.js 4.4.1 on cdnjs; the page has no other dependencies.

## The data

`films.csv` lives next to the page in the repository and is read on every visit. One row per
diary entry, with these columns (header names matter, order doesn't):

| Column | Content |
|---|---|
| `title` | film title |
| `film_year` | release year (`2019` or `2019.0` both work) |
| `watched_date` | `YYYY-MM-DD` (also accepts `M/D/YYYY` and `D.M.YYYY`) |
| `rating` | 0.5–5 |
| `tags` | comma-separated Letterboxd tags, any case |
| `review` | your written review, if any |
| `link` | the Letterboxd diary/film URL |
| `poster_url` (or `poster`, `image`) | optional — an image URL; when present, *Recent watches* shows it instead of a title tile |
| `rewatch` | optional — Yes/No (the RSS feed has carried it since 2024). A viewing also counts as a rewatch when an earlier entry for the same film exists in the file. The `…/film/<slug>/1/` link suffix is deliberately *not* used as a signal: Letterboxd adds it whenever the film was already marked watched, with or without a diary entry, so it flags first viewings of older titles too. Shown as a badge in *Latest reviews*, *Films by rating* and the *Last watched* tile, and counted in the *Films logged* tile |
| `tmdb_id` | optional — used by `fetch_descriptions.py` for an exact TMDB lookup; otherwise the film is searched by title and year |

Titles in the RSS feed's form (`The Odyssey, 2026 - ★★★★★`) are cleaned to the bare title, and the year is taken from them if `film_year` is empty. Rows without a title are skipped. Rows without a date are counted in totals but not in
date-based charts; rows without a rating are excluded from rating charts.

Things worth knowing:

- *Recent watches* reads the image size from Letterboxd's URL (`…-0-600-0-900-crop` is a portrait
  poster, `…-1200-1200-675-675-crop` a 16:9 still) and switches the whole grid to 16:9 tiles when
  most of the shown images are stills. Posters come from the film page (or the RSS item); the
  16:9 still is the review page's share image — the scraper should prefer the former.
  A broken image falls back to a title tile.
- When a `review` column is present, *Latest reviews* shows the newest six in the selection and
  the table gets a Review column (click a cell to expand); without it the card is hidden. Each
  review tile is tinted with its rating's colour from `RATING_COLORS` (a faint top-to-bottom wash).
- Entries without a watched date are counted in totals but not in date-based charts.
- GitHub's raw CDN caches for up to five minutes, so a commit can take that long to show.

### Film descriptions (`descriptions.json`)

`fetch_descriptions.py` runs right after the scraper in the nightly Action and asks
[TMDB](https://www.themoviedb.org/) for a synopsis of every film not yet in `descriptions.json`
(exact lookup when the row has a `tmdb_id`, otherwise a title + year search, accepted when the
release year is within a year of Letterboxd's). The first run fetches everything, later runs only
the new diary entries. Films it could not match are listed under `"misses"` in the file with a
reason, and retried the next night; if one keeps missing, add its `tmdb_id` to the CSV row.

The script needs a free TMDB API key in the repository secret `TMDB_API_KEY`
(Settings → Secrets and variables → Actions → New repository secret; get the key at
themoviedb.org → Settings → API). Without the secret the step logs a warning and the nightly
job carries on as before. TMDB's terms ask for the attribution that sits in the footer's
*About the data*.

On the page, `descriptions.json` is read alongside `films.csv`. When it is there, *Latest reviews*
gets a **Review | Description** toggle (remembered in the browser): *Description* shows the latest
six films in the selection with their synopsis, whether or not they were reviewed, and the table
shows a small ⓘ after every title that has one — click it to open the synopsis under the row. When
the file is missing (as in the drop-in viewer) nothing changes.

## Privacy

The repository is public, so `films.csv` is readable by anyone — fine for a film diary,
but don't add private columns to it.
