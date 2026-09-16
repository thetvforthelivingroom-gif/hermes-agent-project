"""research_agent.py

A command‑line utility that, given a URL, gathers background information,
generates a concise article using an LLM, fetches a royalty‑free image from
Unsplash, and writes the result as Markdown with front‑matter.

Usage
-----
    python research_agent.py <URL>

Environment variables
---------------------
* ``OPENAI_API_KEY`` – API key for the OpenAI Chat Completion endpoint. The
  script uses ``gpt-4o-mini`` for speed and cost‑effectiveness.
* ``UNSPLASH_ACCESS_KEY`` – Access key for the Unsplash API (public image
  search). See https://unsplash.com/documentation#search‑photos.

Both variables can be placed in a ``.env`` file in the project root; the
script loads them with ``python‑dotenv`` if available, otherwise falls back to
the OS environment.
"""

import os
import sys
import re
import json
import hashlib
import datetime
from urllib.parse import urlparse, quote_plus

# Optional third‑party helpers – we import lazily so that the script still runs
# when they are missing (the user can install them with ``pip install -r
# requirements.txt``).
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = lambda *a, **k: None

try:
    import requests
except ImportError:  # pragma: no cover
    print("Error: 'requests' library is required. Install with 'pip install requests'.", file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    print("Error: 'beautifulsoup4' library is required. Install with 'pip install beautifulsoup4'.", file=sys.stderr)
    sys.exit(1)

# Load .env if present
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not set in environment.", file=sys.stderr)
    sys.exit(1)
if not UNSPLASH_ACCESS_KEY:
    print("Error: UNSPLASH_ACCESS_KEY not set in environment.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------

def slugify(text: str) -> str:
    """Create a filesystem‑safe slug from a title.
    Lower‑case, replace non‑alphanum with hyphens, collapse repeats.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or hashlib.sha1(text.encode()).hexdigest()[:8]

def fetch_open_graph(url: str) -> dict:
    """Return a dict of OpenGraph meta tags from the page.
    Keys include ``og:title``, ``og:description``, ``og:image`` when present.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    og = {}
    for tag in soup.find_all("meta"):
        if tag.get("property", "").startswith("og:"):
            og[tag["property"]] = tag.get("content", "")
    return og

def fetch_related(url: str, limit: int = 3) -> list:
    """Very simple related‑article finder using DuckDuckGo's "related:" operator.
    Returns a list of URLs.
    """
    query = f"related:{url}"
    api = f"https://duckduckgo.com/html?q={quote_plus(query)}"
    resp = requests.get(api, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for a in soup.select('a.result__a')[:limit]:
        href = a.get('href')
        if href:
            results.append(href)
    return results

def generate_prompt(main_url: str, og: dict, related: list) -> str:
    """Compose a prompt for the LLM.
    We provide title, description, and short excerpts from related articles.
    """
    title = og.get("og:title", "[No title]")
    desc = og.get("og:description", "[No description]")
    prompt = f"Write a concise, factual news article (≈300‑400 words) about the topic described below.\n\n"
    prompt += f"Title hint: {title}\n\nDescription: {desc}\n\n"
    if related:
        prompt += "Incorporate information from the following related sources (give a brief mention, do not quote directly):\n"
        for u in related:
            prompt += f"- {u}\n"
    prompt += "\nThe article should be written in a neutral tone, include a clear lead paragraph, and end with a short conclusion. Do NOT include any HTML or Markdown formatting beyond what will be placed in the final file."
    return prompt

def call_openai_chat(prompt: str) -> str:
    """Call OpenAI Chat Completion (gpt‑4o‑mini) and return the content.
    The function raises on non‑200 responses.
    """
    endpoint = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

def fetch_unsplash_image(query: str) -> str:
    """Search Unsplash for a royalty‑free image and return its raw URL.
    Returns empty string if none found.
    """
    endpoint = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape",
    }
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    resp = requests.get(endpoint, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return ""
    # Prefer the raw image for maximum resolution
    return results[0]["urls"]["raw"]

def write_markdown(slug: str, title: str, body: str, image_url: str) -> str:
    """Write the final Markdown file and return its absolute path."""
    dt = datetime.datetime.utcnow().isoformat() + "Z"
    front = [
        "---",
        f"title: \"{title}\"",
        f"date: {dt}",
        f"image: {image_url if image_url else ''}",
        "---",
        "",
    ]
    content = "\n".join(front) + body.rstrip() + "\n"
    out_dir = os.path.join(os.getcwd(), "content", "articles")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)
    return path

# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python research_agent.py <URL>")
        sys.exit(1)
    url = sys.argv[1]
    # Step 1 – fetch OpenGraph metadata
    try:
        og = fetch_open_graph(url)
    except Exception as e:
        print(f"Failed to fetch OpenGraph data: {e}", file=sys.stderr)
        sys.exit(1)
    # Step 2 – get a few related URLs for context
    related = fetch_related(url)
    # Step 3 – craft LLM prompt & generate article
    prompt = generate_prompt(url, og, related)
    try:
        article = call_openai_chat(prompt)
    except Exception as e:
        print(f"OpenAI request failed: {e}", file=sys.stderr)
        sys.exit(1)
    # Step 4 – pick an image based on title or first 5 words
    title = og.get("og:title", "Untitled")
    image_query = title
    image_url = fetch_unsplash_image(image_query)
    # Step 5 – write markdown file
    slug = slugify(title)
    out_path = write_markdown(slug, title, article, image_url)
    print(f"Article written to: {out_path}")

if __name__ == "__main__":
    main()
