#!/usr/bin/env python3
"""Source credibility whitelist check.

Defines a whitelist of trusted news domains and provides a function to
validate a URL. When used as a script, it reads a URL from the command
line, prints ``allowed`` or ``rejected`` and logs the decision.
"""
import sys
import urllib.parse
import datetime
import json
import os

# Trusted domains (no protocol, no subdomains)
WHITELIST = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "techcrunch.com",
]

LOG_PATH = os.path.join(os.path.dirname(__file__), "whitelist_audit.log")

def extract_domain(url: str) -> str:
    """Return the hostname part of a URL (lower‑cased)."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        return host.lower()
    except Exception:
        return ""

def is_trusted(url: str) -> bool:
    """Check whether the URL's domain is in the whitelist.

    Subdomains are allowed as long as the base domain matches one of the
    entries in ``WHITELIST``.
    """
    domain = extract_domain(url)
    for trusted in WHITELIST:
        if domain == trusted or domain.endswith('.' + trusted):
            return True
    return False

def log_decision(url: str, allowed: bool) -> None:
    """Append an audit line to ``LOG_PATH``.

    Format (JSON per line):
    {"timestamp": "ISO8601", "url": "...", "allowed": true}
    """
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "url": url,
        "allowed": allowed,
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Logging should never crash the caller; print to stderr.
        print(f"Failed to write audit log: {e}", file=sys.stderr)

def main():
    if len(sys.argv) != 2:
        print("Usage: source_whitelist.py <url>", file=sys.stderr)
        sys.exit(2)
    url = sys.argv[1]
    allowed = is_trusted(url)
    log_decision(url, allowed)
    print("allowed" if allowed else "rejected")
    sys.exit(0 if allowed else 1)

if __name__ == "__main__":
    main()
