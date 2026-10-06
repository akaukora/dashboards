> The READMEs in this repository were written by an AI assistant from Antti's instructions — see [About these READMEs](../README.md#about-these-readmes).

# World Cup 2026 — how the pool was won

The story of a FIFA World Cup 2026 prediction pool among 23 entrants, live at `https://akaukora.github.io/dashboards/wc2026/`.

The game had nine separately scored parts — group-game score predictions, group bottom picks, each knockout round from the round of 32 to the semi-finals, finalists and champion, top scorer, and cards; the page shows the top five in each part, then steps round by round through the eight scoring rounds so you can watch the table change as the tournament went on, up to the final day when the title was decided by a single pick.

## Files

- `index.html` — the whole page. The pool's results are embedded in the file (`DATA` for the entrants' scores by part and round, `STEPS` for the round-by-round narrative, `PODIUM` for the final top three). No network requests and nothing to refresh: the tournament is over.

## Reusing it

The page is a template for telling the story of any pool with a round structure: replace the three embedded arrays with your own pool's scores and text. The entrants appear as “Entrant 01” to “Entrant 23”, not by name.
