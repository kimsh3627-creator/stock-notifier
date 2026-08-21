import sys
import requests
from bs4 import BeautifulSoup


def fetch_top10():
    url = "https://www.genie.co.kr/chart/top200"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("Request error:", e, file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # Try a few likely selectors to be resilient to small markup changes
    rows = []
    selectors = [
        "table.list-wrap tbody tr",
        "#body-content table.list-wrap tbody tr",
        "div.music-list-wrap table tbody tr",
    ]
    for sel in selectors:
        rows = soup.select(sel)
        if rows:
            break

    if not rows:
        # Fallback: look for elements that contain title/artist classes
        rows = soup.select("tr")

    results = []
    for r in rows:
        if len(results) >= 10:
            break

        # Try multiple ways to find title and artist
        title_tag = (
            r.select_one("a.title")
            or r.select_one("td.info a.title")
            or r.select_one(".info .title")
            or r.select_one(".ellipsis.rank01 a")
        )
        artist_tag = (
            r.select_one("a.artist")
            or r.select_one(".info .artist a")
            or r.select_one(".ellipsis.rank02 a")
        )

        if not title_tag or not artist_tag:
            # skip rows that don't look like chart entries
            continue

        title = " ".join(title_tag.get_text(strip=True).split())
        artist = " ".join(artist_tag.get_text(strip=True).split())
        results.append((title, artist))

    return results


def main():
    top10 = fetch_top10()
    if not top10:
        print("Could not find chart entries. The site may require JavaScript or changed markup.")
        return

    for i, (title, artist) in enumerate(top10, start=1):
        print(f"{i:2}. {title} — {artist}")


if __name__ == "__main__":
    main()
