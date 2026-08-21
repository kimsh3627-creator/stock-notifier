# Genie Music Top 10 Scraper

Simple Python script that fetches Genie Music's real-time Top 200 chart and prints the Top 10 titles and artists to the terminal.

Usage:

1. Create a virtualenv (optional) and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate    # On Windows use `.venv\Scripts\activate`
pip install -r requirements.txt
```

2. Run the script:

```bash
python genie_top10.py
```

Notes:
- If the script prints no results, the site may rely on JavaScript or its markup may have changed.
- You can tweak the selectors in `genie_top10.py` if needed.
