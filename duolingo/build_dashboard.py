#!/usr/bin/env python3
"""
Regenerate the static dashboard page from data/weekly_duolingo.json.

Run this after parse_duolingo.py adds new weeks (the GitHub Actions workflow
does this automatically). Writes to index.html right here in this folder, so
GitHub Pages can serve it straight from the repo root (each dashboard is its
own top-level folder, e.g. akaukora.github.io/dashboards/duolingo/).

dashboard_template.html is a bare content fragment (title/link/style, then
the page body, then a script) with no <!DOCTYPE>/<html>/<head>/<body> of its
own -- that's deliberate, since the same fragment is also pasted into an
Artifact-hosted preview that supplies its own document shell. GitHub Pages
serves this file standalone though, with nothing to wrap it, so this script
adds a real HTML5 document shell around it -- crucially including the
viewport meta tag, without which mobile browsers render it as a shrunk-down
desktop page instead of a responsive one.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "weekly_duolingo.json")
TEMPLATE_PATH = os.path.join(HERE, "dashboard_template.html")
OUT_PATH = os.path.join(HERE, "index.html")

DOC_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
"""
DOC_MID = "</head>\n<body>\n"
DOC_TAIL = "\n</body>\n</html>\n"


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    template = open(TEMPLATE_PATH, encoding="utf-8").read()
    filled = template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))

    # Split the fragment right after the closing </style> tag: everything
    # before it (title/link/style) is genuine <head> content, everything
    # after (the page markup + the closing <script>) is <body> content.
    marker = "</style>"
    idx = filled.index(marker) + len(marker)
    head_content, body_content = filled[:idx], filled[idx:]

    out = DOC_HEAD + head_content + DOC_MID + body_content + DOC_TAIL
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {OUT_PATH} with {len(data)} weeks.")


if __name__ == "__main__":
    main()
