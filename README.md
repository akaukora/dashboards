# Dataviz gallery

The gallery is at **<https://akaukora.github.io/dashboards/>**. This repository holds the files behind it: one folder per piece, each with the page (`index.html`), its data and, where there is one, the script and GitHub Actions workflow that keep the data fresh. The Tableau vizzes shown in the gallery live on [Tableau Public](https://public.tableau.com/app/profile/antti1275) and are not in this repository.

## What's here

| Folder | What it is | Data |
|---|---|---|
| `films-watched/` | Letterboxd diary since 2019 | `films.csv`, refreshed nightly from the Letterboxd RSS and diary pages; film descriptions from TMDB |
| `books-read/` | StoryGraph library | `books.csv`, a manual StoryGraph export; descriptions from Open Library and Google Books |
| `music/` | Twenty years of Last.fm scrobbles, with forgotten favorites | `scrobbles.csv`, refreshed daily from the Last.fm API, with a Spotify export filling the gaps |
| `duolingo/` | Duolingo time, XP and lessons by week | weekly progress-report emails, parsed by a workflow |
| `prediction-markets/` | Polymarket and Kalshi positions in one view | `data.json`, refreshed twice a day |
| `hiff2026/`, `tiff2026/` | Festival planners for Helsinki (HIFF) and Toronto (TIFF) 2026 | the festival program, embedded in the page |
| `wc2026/` | How a World Cup 2026 prediction pool was won | the pool's results, embedded in the page |
| `violent-protected/` | Two world maps drawn only from data points, no basemap | UCDP GED v26.1 and Protected Planet / WDPA, pre-rendered into the page |
| `task-timeline/` | A task tracker in one markdown file, with a board and timeline on top | a demo `TASKS.md` with fictional tasks |
| `letterboxd-viewer/`, `storygraph-viewer/`, `music-viewer/` | Drop-in versions of the three diaries: open the page, drop your own export on it | your export, parsed in the browser and kept only there |
| `thumbs/` | Thumbnails and the link-preview image for the gallery | |
| `index.html` | The gallery page itself | |
| `gallery-link.js` | The small "← Gallery" link every page shows | |

## How the pieces are built

Every page is a single HTML file. It reads a CSV or JSON from the same folder on load (or, in the viewers, a file you drop on it) and draws everything in the browser; there is no build step and no server. The pages that refresh themselves do so through scheduled GitHub Actions workflows in `.github/workflows/`, which run a Python script, commit the new data file and let GitHub Pages serve the result. Credentials live in the repository's Actions secrets, never in the files.

The shared look (a dark Letterboxd-like palette with a cream light theme, following the system setting) is described in the gallery page's styles; each page carries its own copy of the tokens it needs.

## About these READMEs

I design the visualizations. The READMEs in each folder were written by the AI assistant that built the page with me, from my instructions. The parts I rely on myself — the data pipelines and scraper behavior — I've read and use. The rest I haven't proofread, so if something is unclear, open an issue.

## Reuse

Take any folder and rebuild it around your own data; the READMEs explain what each page expects. The three viewers need no setup at all.
