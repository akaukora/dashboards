# Letterboxd diary viewer

A drop-in version of the film diary dashboard for anyone with a Letterboxd account. One
self-contained `index.html`: the visitor drops the CSV files from their Letterboxd export on
the page and gets the dashboard for their own diary. Nothing is uploaded — the files are parsed
in the browser and kept only in that browser's local storage.

Live at `https://akaukora.github.io/dashboards/letterboxd-viewer/` once this folder is in the
`dashboards` repository as `letterboxd-viewer/`. The relative links in the page
(`../films-watched/`) assume it sits next to the personal dashboard.

## What a visitor does

1. On Letterboxd: **Settings → Data → Export your data**, then unzip the download.
2. Drop `diary.csv` on the page — plus `reviews.csv` for the review cards. Several files at
   once is fine; a reviews file dropped later joins the diary already loaded. The "Choose
   files…" button does the same through a file picker.
3. The data stays in the browser until **Forget my data** is pressed, so the page can be
   reopened later without re-dropping. Nothing else is stored anywhere.

The page also accepts a `films.csv` in the personal dashboard's format, and a hosted CSV via
`?src=<raw URL>` (a GitHub raw or Gist raw link; those are not kept in local storage).

Files without a *Watched Date* column (`ratings.csv`, `watched.csv`, `watchlist.csv`) are refused
with a hint, because their *Date* is when the film was added, not when it was watched.

## What is different from the personal dashboard

- **Tags are generic.** The personal dashboard reads a private taxonomy from tags (service,
  venue, theater roll-up). Nobody else's tags follow it, so here tags are just filter buttons
  for the most-used ones (`MIN_TAG_CHIP` entries needed, at most `MAX_TAG_CHIPS` shown), and
  appear in tooltips, review cards and the table, spelled as they are in the file. The
  *Ratings by service* chart, its Mekko view, the Source buttons and the theater tile are gone.
- The fourth KPI tile is **Rewatches** (with the count of written reviews) instead of the
  theater share.
- `RATING_MEANING` uses neutral words (great / good / ok / weak / poor) instead of a personal
  scale; the five colours are unchanged. Half stars fall into the whole star below them.
- No posters: the export carries none, so *Recent watches* shows title tiles. Links are the
  export's short `boxd.it` URLs and open the film's page on Letterboxd.
- Rewatches come from the export's `Rewatch` column, or from an earlier entry for the same
  film in the file.

Everything else — cross-filtering, the sticky filter bar, the URL hash, the Columns/Lines
toggle, the heatmap, the table view — is the same code. The page is generated from the
personal dashboard by `make_viewer.py` (kept outside the repository), so improvements made
there can be carried over by re-running the script rather than by hand.

## How the files are combined

`diary.csv` rows are the spine. Each `reviews.csv` row is attached to the diary entry with the
same Letterboxd URI and watched date (falling back to same title and date); if none matches
the row is added as an entry. A newly dropped diary replaces the previous one; a newly dropped
reviews file replaces the previous reviews file. If only `reviews.csv` is dropped, it is used
as a partial diary.

## Privacy

Local storage is per browser and per site, so data dropped on the GitHub Pages URL is visible
only to that browser. The page makes no network requests apart from loading Chart.js from
cdnjs (and the optional `?src=` CSV).
