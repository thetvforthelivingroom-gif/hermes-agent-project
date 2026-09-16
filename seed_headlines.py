import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import datetime
import os

# Configuration: RSS feed URLs and source names
SOURCES = [
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'),
    ('BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Reuters World', 'https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US&ceid=US:en'),
    ('AP World', 'https://apnews.com/rss/headlines'),
    ('Fox News World', 'http://feeds.foxnews.com/foxnews/world'),
    ('Al Jazeera World', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('NYTimes World', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('NBC World', 'https://feeds.nbcnews.com/nbcnews/public/feeds/worldnews.rss'),
    ('The Guardian World', 'https://www.theguardian.com/world/rss'),
    ('Bloomberg World', 'https://www.bloomberg.com/feed/podcast/worldwide')
]

LOG_PATH = os.path.join(os.path.dirname(__file__), 'seed_headlines.log')
KANBAN_PATH = os.path.join(os.path.dirname(__file__), 'kanban.md')

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()

def parse_rss(content, source_name):
    headlines = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return headlines
    # RSS items
    for item in root.iter('item'):
        title_elem = item.find('title')
        link_elem = item.find('link')
        if title_elem is not None and link_elem is not None:
            title = title_elem.text.strip()
            link = link_elem.text.strip()
            headlines.append({'title': title, 'url': link, 'source': source_name})
    # Atom entries
    for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
        title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
        link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
        if title_elem is not None and link_elem is not None:
            title = title_elem.text.strip()
            link = link_elem.attrib.get('href', '').strip()
            headlines.append({'title': title, 'url': link, 'source': source_name})
    return headlines

def collect_urls():
    urls = set()
    for name, url in SOURCES:
        try:
            data = fetch(url)
            for h in parse_rss(data, name):
                if h['url']:
                    urls.add(h['url'])
        except Exception as e:
            log(f'Error fetching {name}: {e}')
    return urls

def load_existing_urls():
    if not os.path.exists(KANBAN_PATH):
        return set()
    with open(KANBAN_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    urls = set()
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            url = line[2:].strip()
            urls.add(url)
    return urls

def ensure_kanban_structure():
    if not os.path.exists(KANBAN_PATH):
        with open(KANBAN_PATH, 'w', encoding='utf-8') as f:
            f.write('## To-Do\n\n')
        return
    # Ensure a ## To-Do header exists
    with open(KANBAN_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    if '## To-Do' not in content:
        with open(KANBAN_PATH, 'a', encoding='utf-8') as f:
            f.write('\n## To-Do\n\n')

def append_new_urls(new_urls):
    if not new_urls:
        return 0
    with open(KANBAN_PATH, 'a', encoding='utf-8') as f:
        for url in sorted(new_urls):
            f.write(f'- {url}\n')
    return len(new_urls)

def log(message):
    timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'[{timestamp}] {message}\n')

def main():
    ensure_kanban_structure()
    existing = load_existing_urls()
    fetched = collect_urls()
    to_add = fetched - existing
    added = append_new_urls(to_add)
    log(f'Fetched {len(fetched)} URLs, added {added} new URLs to kanban.md')

if __name__ == '__main__':
    main()
