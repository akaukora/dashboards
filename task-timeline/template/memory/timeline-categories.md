# Timeline categories

How categories render on the dashboard timeline. A task's category is the first
`BACKTICK TAG` in its note in TASKS.md.

- **process** — the tasks form one end-to-end process. The category row shows a
  roll-up bar from the earliest start to the latest end, plus a completion %.
  Expanded by default.
- **bag** — the tasks are independent. The category row just groups them.
  Collapsed by default.

The dashboard reads this file when you open the Memory folder, and rewrites it when
you change a category in the timeline's ⚙ category manager. A category that isn't
listed here is treated as **bag**.

```yaml
categories:
  - tag: "BUDGET"
    type: process
    label: "Budget"
  - tag: "REPORTING"
    type: process
    label: "Reporting"

  - tag: "BOARD"
    type: bag
    label: "Board"
  - tag: "LENDERS"
    type: bag
    label: "Lenders"
  - tag: "MONTH-END"
    type: bag
    label: "Month-end"
  - tag: "SURVEYS"
    type: bag
    label: "Surveys"
  - tag: "AD HOC"
    type: bag
    label: "Ad hoc"
```

## Why these choices

- **BUDGET** is a chain: inputs → first draft → CFO review → final version. The
  roll-up shows how far through the cycle you are.
- **LENDERS** reports go to different banks on different schedules, so a roll-up
  would mean nothing.
- **AD HOC** is unrelated by definition. Untagged tasks land here too.
