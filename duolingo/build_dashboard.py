#!/usr/bin/env python3
"""
Regenerate the static dashboard page from data/weekly_duolingo.json.

Run this after parse_duolingo.py adds new weeks (the GitHub Actions workflow
does this automatically). Writes to index.html right here in this folder, so
GitHub Pages can serve it straight from the repo root (each dashboard is its
own top-level folder, e.g. akaukora.github.io/dashboards/duolingo/).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "weekly_duolingo.json")
TEMPLATE_PATH = os.path.join(HERE, "dashboard_template.html")
OUT_PATH = os.path.join(HERE, "index.html")


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    template = open(TEMPLATE_PATH, encoding="utf-8").read()
    out = template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {OUT_PATH} with {len(data)} weeks.")


if __name__ == "__main__":
    main()
