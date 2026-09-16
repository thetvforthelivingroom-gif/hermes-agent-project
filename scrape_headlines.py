import urllib.request
import urllib.parse
import urllib.robotparser

import json
import datetime
import re
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from html.parser import HTMLParser

class HeadlineParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.in_anchor = False
        self.current_href = ''
        self.headlines = []
        self.text_fragments = []
        self.seen = set()
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.in_anchor = True
                self.current_href = urllib.parse.urljoin(self.base_url, href)
                self.text_fragments = []
    def handle_endtag(self, tag):
        if tag == 'a' and self.in_anchor:
            text = ''.join(self.text_fragments).strip()
            # simple filter: length and not too generic
            if len(text) > 6 and not re.search(r'\b(\d{4}|\s+|\b)(\s|$)', text) and text not in self.seen:
                self.headlines.append({
                    'title': text,
                    'url': self.current_href,
                    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
                })
                self.seen.add(text)
            self.in_anchor = False
            self.current_href = ''
    def handle_data(self, data):
        if self.in_anchor:
            self.text_fragments.append(data)

def fetch(url):
    # Respect robots.txt
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(base, '/robots.txt'))
    try:
        rp.read()
    except Exception as e:
        logger.warning(f'Could not read robots.txt from {base}: {e}')
    if not rp.can_fetch('*', url):
        logger.warning(f'Fetching blocked by robots.txt: {url}')
        raise PermissionError(f'Blocked by robots.txt: {url}')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def scrape_source(name, url, max_retries=3):
    """Fetch the given URL with retry and parse headlines.
+
+    Args:
+        name: Human readable source name (e.g., "CNN").
+        url: URL to fetch.
+        max_retries: Number of retry attempts on transient errors.
+
+    Returns:
+        List of headline dicts with ``title``, ``url``, ``timestamp`` and ``source``.
+    """
+    attempt = 0
+    while attempt < max_retries:
+        try:
+            html = fetch(url)
+            break
+        except Exception as e:
+            attempt += 1
+            logger.warning(f'Attempt {attempt}/{max_retries} failed for {name}: {e}')
+            if attempt >= max_retries:
+                logger.error(f'All attempts failed for {name}')
+                return []
+    parser = HeadlineParser(url)
+    parser.feed(html)
+    # Annotate each headline with its source name
+    for h in parser.headlines:
+        h['source'] = name
+    return parser.headlines

sources = [
    ('CNN', 'https://edition.cnn.com/world'),
    ('BBC', 'https://www.bbc.com/news'),
    ('Reuters', 'https://www.reuters.com/world/'),
    ('AP', 'https://apnews.com/hub/world-news'),
    ('Fox News', 'https://www.foxnews.com/world'),
    ('Al Jazeera', 'https://www.aljazeera.com/news/'),
    ('NYTimes', 'https://www.nytimes.com/section/world'),
    ('NBC', 'https://www.nbcnews.com/world'),
    ('The Guardian', 'https://www.theguardian.com/world'),
    ('Bloomberg', 'https://www.bloomberg.com/world')
]

all_headlines = []
for name, url in sources:
    print(f'Scraping {name}...')
    heads = scrape_source(name, url)
    all_headlines.extend(heads)

# deduplicate by title
unique = {h['title']: h for h in all_headlines}
result = list(unique.values())
# sort by timestamp descending (newest first)
result.sort(key=lambda x: x['timestamp'], reverse=True)
# ensure at least 100 headlines, otherwise warn
if len(result) < 100:
    print(f'Warning: only collected {len(result)} headlines')

output_path = 'headlines.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'Saved {len(result)} headlines to {output_path}')
