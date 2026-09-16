#!/usr/bin/env python3
"""Validate Unsplash image sizes and replace oversized images.

Usage:
    python3 validate_unsplash_images.py <input_file> <output_file>

* <input_file>  – newline‑separated list of image URLs.
* <output_file> – file where the resulting URLs are written, one per line.

Oversized images (Content‑Length > 200 KB or missing header) are replaced by
PLACEHOLDER_URL.
Logs are written to 'unsplash_image_validation.log' in the same directory.
"""

import sys
import subprocess
import shlex
from pathlib import Path

PLACEHOLDER_URL = "https://images.unsplash.com/photo-placeholder"
MAX_BYTES = 200 * 1024  # 200 KB

LOG_PATH = Path(__file__).with_name("unsplash_image_validation.log")

def log(msg: str) -> None:
    # Append log entry, creating the file if it does not exist.
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def header_content_length(url: str) -> int | None:
    """Return Content‑Length in bytes or None if unavailable or on error."""
    try:
        # Use curl -I --silent to get only headers.
        result = subprocess.run(
            ["curl", "-I", "--silent", url],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            log(f"ERROR fetching headers for {url}: exit {result.returncode}")
            return None
        for line in result.stdout.splitlines():
            if line.lower().startswith("content-length:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError:
                    return None
        # Header not present → treat as oversized per spec.
        return None
    except Exception as e:
        log(f"EXCEPTION for {url}: {e}")
        return None

def process(input_path: Path, output_path: Path) -> int:
    if not input_path.is_file():
        log(f"INPUT file missing: {input_path}")
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as fin, output_path.open("w", encoding="utf-8") as fout:
        for raw in fin:
            url = raw.strip()
            if not url:
                continue
            size = header_content_length(url)
            if size is None or size > MAX_BYTES:
                log(f"REPLACE {url} – size {'missing' if size is None else size} > {MAX_BYTES}")
                fout.write(PLACEHOLDER_URL + "\n")
            else:
                fout.write(url + "\n")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: validate_unsplash_images.py <input_file> <output_file>")
        sys.exit(2)
    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])
    sys.exit(process(inp, outp))
