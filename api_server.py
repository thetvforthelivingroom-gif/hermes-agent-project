#!/usr/bin/env python3
"""Simple API server to serve articles sorted by timestamp.

# Endpoint: GET /api/articles
# Endpoint: GET /api/stories/status
Query parameters:
  page (int, default 1)      - page number (1-indexed)
  limit (int, default 10)    - items per page
  start (ISO datetime, optional) - include articles with timestamp >= start
  end (ISO datetime, optional)   - include articles with timestamp <= end

The server loads articles from a JSON file (default 'headlines.json') in the same directory.
Each article is expected to have a 'timestamp' field in ISO 8601 format.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "headlines.json")

def load_articles():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure it's a list
        if isinstance(data, dict) and "articles" in data:
            articles = data["articles"]
        else:
            articles = data
        return articles
    except Exception as e:
        sys.stderr.write(f"Failed to load articles: {e}\n")
        return []

def parse_iso(ts):
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None

class SimpleAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        # Articles endpoint
        if parsed.path == "/api/articles":
            query = parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])
            limit = int(query.get("limit", ["10"])[0])
            start = query.get("start", [None])[0]
            end = query.get("end", [None])[0]

            articles = load_articles()
            # Filter by date if provided
            if start:
                start_dt = parse_iso(start)
                if start_dt:
                    articles = [a for a in articles if parse_iso(a.get("timestamp", "")) and parse_iso(a["timestamp"]) >= start_dt]
            if end:
                end_dt = parse_iso(end)
                if end_dt:
                    articles = [a for a in articles if parse_iso(a.get("timestamp", "")) and parse_iso(a["timestamp"]) <= end_dt]

            # Sort by timestamp descending
            articles.sort(key=lambda a: parse_iso(a.get("timestamp", "")) or datetime.min, reverse=True)

            # Pagination
            total = len(articles)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_items = articles[start_idx:end_idx]

            response = {
                "page": page,
                "limit": limit,
                "total": total,
                "articles": page_items,
            }
            self._send_json(response)
            return
        # New stories status endpoint
        if parsed.path == "/api/stories/status":
            # Load stories data
            stories_path = os.path.join(os.path.dirname(__file__), "stories.json")
            try:
                with open(stories_path, "r", encoding="utf-8") as f:
                    stories = json.load(f)
            except Exception as e:
                self._send_json({"error": f"Failed to load stories: {e}"}, status=500)
                return

        # Determine kanban stage by checking presence in kanban.md and optional story_stages.json for detailed stages
        kanban_path = os.path.join(os.path.dirname(__file__), "kanban.md")
        kanban_urls = set()
        try:
            with open(kanban_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- "):
                        url = line[2:].strip()
                        kanban_urls.add(url)
        except Exception:
            pass
        # Load detailed stages if available
        stages_path = os.path.join(os.path.dirname(__file__), "story_stages.json")
        story_stage_map = {}
        try:
            with open(stages_path, "r", encoding="utf-8") as f:
                story_stage_map = json.load(f)
        except Exception:
            pass

        result = []
        for idx, story in enumerate(stories, start=1):
            story_id = idx
            title = story.get("title", "")
            url = story.get("url", "")
            # Prefer detailed stage mapping, fallback to todo/none based on kanban presence
            if url in story_stage_map:
                stage = story_stage_map[url]
            else:
                stage = "todo" if url in kanban_urls else "none"
            result.append({"id": story_id, "title": title, "stage": stage})


            self._send_json({"stories": result})
            return
        # Fallback for unknown paths
        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Suppress default logging
        return

def run(server_class=HTTPServer, handler_class=SimpleAPIHandler, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting API server on port {port} (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == "__main__":
    run()
