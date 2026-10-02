# Recurring tasks — rules

Tasks that repeat on a fixed cadence. Each rule is **materialized** as concrete dated
tasks in `TASKS.md` for a rolling window (default 12 months ahead). The weekly update
tops the series up when its last instance gets closer than 6 months.

Two ways to repeat a task — use whichever fits:

1. **A rule in this file** (below). Best for frequent cadences (monthly) where you want
   to see the whole year on the timeline. The assistant adds instances during the
   weekly update.
2. **A `[↻ monthly|quarterly|annual]` marker in the task note.** Best for one-off
   yearly or quarterly items. When you tick the task done in the dashboard, it creates
   the next instance automatically, with the dates shifted by the cadence.

**Weekend rule for all generated dates:** if an end date lands on Saturday or Sunday,
move it back to Friday and move the start by the same number of days, so the prep
window keeps its length.

## Rule format

```
### <Task title>
- **Cadence:** monthly | quarterly | annual | every N weeks/months
- **Anchor:** which day(s) of the month / which months of the year
- **Duration:** prep window in days (default 7)
- **Category tag:** `MONTH-END` etc.
- **Section:** Not started (default) | Active | Urgent | Waiting for others | Some day
- **Note template:** text that goes after the date range
- **Materialize:** how far ahead to keep instances (default 12 months)
- **Confirmed:** yes / no   ← rules marked "no" are skipped until you confirm them
```

---

## Monthly

### Month-end close
- **Cadence:** monthly
- **Anchor:** end = 2nd working day of the following month; start = end − 7 days
- **Duration:** 7 days
- **Category tag:** `MONTH-END`
- **Section:** Not started
- **Title pattern:** `Month-end close — MM/YYYY`
- **Note template:** `monthly close (deadline 2nd working day)`
- **Materialize:** 12 months
- **Confirmed:** yes

## Quarterly

### Lender covenant report — quarterly
- **Cadence:** quarterly (Q1, Q2, Q3 — Q4 is covered by the annual FY report)
- **Anchor:** deadline = last working day of the month after quarter end
- **Duration:** 14 days (the calculations need more than the default week)
- **Category tag:** `LENDERS`
- **Section:** Not started
- **Title pattern:** `Lender covenant report Q<n> <YYYY>`
- **Note template:** `Quarterly compliance certificate to the bank.`
- **Materialize:** 12 months
- **Confirmed:** no   ← example of a rule waiting for confirmation

## Not recurring (on purpose)

Write down things that *look* recurring but shouldn't be generated, so the assistant
doesn't keep suggesting them, e.g.:

- **Monthly P&L from accounting** — Sam emails it; no task needed.
