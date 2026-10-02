# Instructions for AI assistants

You're helping a user run a markdown-based task tracker. Read this file first, then the
files it points to. The instructions are plain markdown; nothing here is specific to
one AI product.

## The working folder

The user keeps one folder (not this repository) with:

| File | What it is |
|------|------------|
| `TASKS.md` | All tasks, one per line, in sections. The single source of truth. |
| `CLAUDE.md` | Working memory: who the user is, frequent people/terms/projects, preferences, and the **task-list rules**. The name is historical; treat it as your instructions file. |
| `memory/` | Glossary, people, projects, recurring rules, dismissed suggestions, category settings, archive. |
| `dashboard.html` | The user's visual view of `TASKS.md`. You don't need to run it. |

If the folder doesn't exist yet, set it up as described in `skills/start/SKILL.md`,
using `template/` as the example.

## What to read

- `skills/task-management/SKILL.md` — the task line format and how to add, complete,
  move and report on tasks.
- `skills/memory-management/SKILL.md` — how to look up and record people, terms and projects.
- `skills/update/SKILL.md` — the weekly review, step by step.
- The user's own `CLAUDE.md` — their rules win over the defaults in this repository.

(`${CLAUDE_PLUGIN_ROOT}` in those files means the root of this repository.)

## Ground rules

1. **Edit files, don't rewrite them.** Change the specific lines with a read-modify-write
   of the real file. Never retype a whole file from memory or from earlier output.
2. **Keep the format exact.** The dashboard parses `**Title**`, the
   `[YYYY-MM-DD → YYYY-MM-DD]` range (with the → arrow), the first backtick tag as the
   category, `[↻ cadence]`, and `[label](https://…)` links. Keep `##` section headings.
3. **Titles are identifiers.** The weekly diff matches tasks by bold title; don't
   rename tasks casually and keep titles unique.
4. **Suggest, don't add.** Tasks found in email, chat or meeting notes are suggestions
   until the user confirms them. You may change without asking only: recurring
   instances from `memory/recurring.md`, archive moves of old completed tasks, and the
   snapshot in `memory/.update-snapshots/`.
5. **Dates:** follow the date defaults and the weekend rule in the user's `CLAUDE.md`.

## Scheduling

If your tool can run prompts on a schedule *and* edit files in the user's folder, the
weekly review can run on its own: use `prompts/weekly-update.md`. If it can't, the user
asks for "the weekly update" by hand.
