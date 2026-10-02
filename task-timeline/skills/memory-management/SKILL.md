---
name: memory-management
description: Two-tier workplace memory — CLAUDE.md as a hot cache and a memory/ folder as the full knowledge base — so the assistant decodes the user's shorthand, nicknames, acronyms and project codenames like a colleague would. Use when a request contains unfamiliar names or terms, or when the user says "remember", "X means Y" or "who is X".
user-invocable: false
---

# Memory management

Memory turns shorthand into something actionable:

```
User: "send the pack to Maria before the Harbor call"
          ↓ decoded from memory
"Send the monthly KPI report to Maria Lind (CFO) before the call about the
 harbor-front portfolio purchase."
```

## Architecture

```
CLAUDE.md          ← hot cache: top people, terms, active projects, preferences, task-list rules
memory/
  glossary.md      ← full decoder ring
  people/          ← one file per person
  projects/        ← one file per project or codename
  context/         ← organisation, tools, processes (optional)
  recurring.md     ← recurring task rules (see task-management / update)
  dismissed-suggestions.md
  timeline-categories.md
  archive/         ← completed tasks older than 90 days
```

**CLAUDE.md** should cover ~90 % of everyday decoding and stay under ~100 lines.
**memory/** can grow without limit and is read only when needed.

## Lookup order

1. CLAUDE.md
2. memory/glossary.md
3. memory/people/ or memory/projects/ for detail
4. Still unknown or ambiguous (two people called Sam?) → ask the user, then save the answer

## Adding memory

When the user says "remember…", "X is Y", or answers a question about a term:

- **Term / acronym / codename** → memory/glossary.md; promote to CLAUDE.md if it comes up often.
- **Person** → memory/people/<first-last>.md (lowercase, hyphens) with nicknames,
  role and how they prefer to communicate; add to the CLAUDE.md table if frequent.
- **Project** → memory/projects/<name>.md with the codename *and* the full name.
- **Preference** → the Preferences section of CLAUDE.md.

## Promotion and demotion

- Promote to CLAUDE.md when something is used often or is part of current work.
- Demote to memory/ only when a project ends or a person is no longer a frequent contact.
- Never delete history; move it.

## Conventions

- Tables for compact lookup; **bold** names in CLAUDE.md.
- Always capture nicknames and alternate spellings.
- Don't store anything sensitive (personal identity numbers, health, salaries) unless
  the user explicitly asks and it's needed for their work.
