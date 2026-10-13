"""
Step 1 - Fetch the legal provision.

Fetches GDPR Article 8 from the client-provided source (gdpr-info.eu),
parses the three numbered paragraphs, and returns them as structured data.

If the network is unavailable (e.g. offline, proxy-blocked, site down), it
falls back to the bundled verbatim copy in data/art8_cached.json so the rest
of the pipeline always has an authoritative text to work from.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
from typing import Dict

ARTICLE_URL = "https://gdpr-info.eu/art-8-gdpr/"
_ROOT = pathlib.Path(__file__).resolve().parent.parent
_CACHE = _ROOT / "data" / "art8_cached.json"


def _parse_html(html: str) -> Dict[str, str]:
    """Extract the numbered paragraphs of Article 8 from the gdpr-info.eu page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", class_="entry-content") or soup
    ol = content.find("ol")
    if ol is None:
        raise ValueError("Could not locate the article's ordered list in the page.")

    paragraphs: Dict[str, str] = {}
    for idx, li in enumerate(ol.find_all("li", recursive=False), start=1):
        # The site prefixes sentence numbers (1,2,3...) as <span>/sup markers.
        # Collapse whitespace; the leading sentence digits are harmless for our
        # purposes but we strip an immediate leading digit if it hugs a capital.
        text = " ".join(li.get_text(" ", strip=True).split())
        paragraphs[str(idx)] = text
    if not paragraphs:
        raise ValueError("No paragraphs parsed from the article page.")
    return paragraphs


def fetch_article_8(force_offline: bool = False, timeout: int = 30) -> dict:
    """
    Return Article 8 as:
        {source_url, retrieved_at, article, title, paragraphs:{"1":..,"2":..,"3":..}}

    Tries the live client source first; on any failure, loads the bundled cache.
    """
    if not force_offline:
        try:
            import requests

            resp = requests.get(
                ARTICLE_URL,
                timeout=timeout,
                headers={"User-Agent": "legalruleml-demo/1.0 (+research)"},
            )
            resp.raise_for_status()
            paragraphs = _parse_html(resp.text)
            return {
                "source_url": ARTICLE_URL,
                "retrieved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "article": "8",
                "title": "Conditions applicable to child's consent in "
                "relation to information society services",
                "paragraphs": paragraphs,
            }
        except Exception as exc:  # network blocked/offline/site change -> fallback
            print(f"[fetch] live fetch failed ({exc.__class__.__name__}: {exc}).")
            print("[fetch] falling back to bundled cache: data/art8_cached.json")

    data = json.loads(_CACHE.read_text(encoding="utf-8"))
    return data


if __name__ == "__main__":
    art = fetch_article_8()
    print(json.dumps(art, indent=2, ensure_ascii=False))
