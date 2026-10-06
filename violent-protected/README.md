> The READMEs in this repository were written by an AI assistant from Antti's instructions — see [About these READMEs](../README.md#about-these-readmes).

# Violent and protected world

Two world maps drawn only from data, with no basemap underneath, live at `https://akaukora.github.io/dashboards/violent-protected/`. A toggle switches between them.

**Violent world** — the world divided into half-degree squares, each colored by the deaths from organized violence recorded there between 1989 and 2025: 355 217 events and 2 954 934 deaths over 37 years. The shape of the continents emerges from where people died.

**Protected world** — the same squares, colored by the protected areas of 2026: 262 050 areas set aside for nature across 272 countries and territories, which draw a fuller, greener outline of the same planet.

The piece is the next generation of a 2018 Tableau viz on riot and protest violence.

## Data

- Violence: [UCDP Georeferenced Event Dataset (GED) v26.1](https://ucdp.uu.se/), Uppsala Conflict Data Program. Each event has coordinates, a date and a best estimate of deaths. Only events located to district precision or better are used (355 217 of 417 968); they are summed into the half-degree squares.
- Protected areas: [Protected Planet — World Database on Protected Areas (WDPA) and WD-OECM](https://www.protectedplanet.net/), September 2026 release, UNEP-WCMC and IUCN, mapped onto the same squares.

Both datasets were processed offline into the point grids embedded in `index.html`; the page itself makes no network requests and draws the grids on a canvas.

## Files

- `index.html` — the page with both grids embedded.
