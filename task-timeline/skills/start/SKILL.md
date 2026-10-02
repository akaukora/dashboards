---
name: start
description: Set up the task timeline and memory system in the current folder and open the dashboard. Use on first use, or when the user asks to set up, initialise or bootstrap their task tracker, or to learn the shorthand in their existing to-do list.
---

# Start

Set up the task list, memory and dashboard in the current working folder, then help
the user bring in their existing tasks.

## 1. Check what exists

Look in the working folder for `TASKS.md`, `CLAUDE.md`, `memory/` and `dashboard.html`.

## 2. Create what's missing

- **dashboard.html** → copy from `${CLAUDE_PLUGIN_ROOT}/skills/dashboard.html`.
- **TASKS.md** → create the empty template from the task-management skill. Ask whether
  the user would rather start from the fictional example in
  `${CLAUDE_PLUGIN_ROOT}/template/TASKS.md` to see every feature first.
- **CLAUDE.md** → copy `${CLAUDE_PLUGIN_ROOT}/template/CLAUDE.md`, then replace the
  fictional "Me / People / Terms / Projects" sections with the user's own (step 4).
  Keep the "Task-list rules" part; walk the user through it and remove or change any
  rule they don't want.
- **memory/** → create `glossary.md`, `recurring.md`, `dismissed-suggestions.md`,
  `timeline-categories.md`, and the `people/`, `projects/` and `archive/` folders, using
  the files under `${CLAUDE_PLUGIN_ROOT}/template/memory/` as a pattern but **without**
  the fictional entries.

Never overwrite an existing file. If something already exists, leave it and say so.

## 3. Open the dashboard

Shell `open` commands may not reach the user's browser, so tell them instead:

> The dashboard is `dashboard.html` in your folder. Open it in Chrome or Edge on a
> desktop, click **Select File** and pick `TASKS.md`. For the Memory tab, click
> **Open Folder** and pick the whole folder.

(It uses the browser's local file access, which desktop Chrome and Edge support and
Safari, Firefox and mobile browsers don't.)

## 4. Bring in existing tasks and learn the shorthand

Ask where their current to-do list lives (another app, a spreadsheet, a notes file,
flagged emails) and ask them to paste or export it. Then:

1. Convert each item to the task line format, with categories and date ranges
   (date defaults and the weekend rule from CLAUDE.md). Show the result before saving.
2. List names, acronyms and codenames you couldn't decode and ask about them, a few
   at a time. Save answers per the memory-management skill.
3. Ask which tasks repeat (monthly reports, quarterly filings, annual cycles) and
   write rules for them in `memory/recurring.md`, marked `Confirmed: yes` once the
   user agrees.
4. Ask which categories are end-to-end processes (roll-up bar) and which are just
   groups, and record that in `memory/timeline-categories.md`.

## 5. Offer the weekly update

Suggest running the update skill weekly, and — if the user's tool supports scheduled
tasks — offer to schedule it using `${CLAUDE_PLUGIN_ROOT}/prompts/weekly-update.md`.

## 6. Report

```
Set up:
- TASKS.md — N tasks in M categories
- Memory — N people, N terms, N projects; N recurring rules
- Dashboard — open dashboard.html in Chrome or Edge
```
