import urllib.request
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
import json
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch(url):
    # Attempt to respect robots.txt but proceed if blocked
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(base, '/robots.txt'))
    try:
        rp.read()
        if not rp.can_fetch('*', url):
            logger.warning(f'Robots.txt disallows fetching {url}; proceeding anyway')
    except Exception as e:
        logger.warning(f'Could not read robots.txt from {base}: {e}')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def parse_rss(content, source_name):
    headlines = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return headlines
    # handle both RSS and Atom
    for item in root.iter('item'):
        title_elem = item.find('title')
        link_elem = item.find('link')
        if title_elem is not None and link_elem is not None:
            title = title_elem.text.strip()
            link = link_elem.text.strip()
            headlines.append({
                'title': title,
                'url': link,
                'source': source_name,
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            })
    # Atom entries
    for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
        title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
        link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
        if title_elem is not None and link_elem is not None:
            title = title_elem.text.strip()
            link = link_elem.attrib.get('href', '').strip()
            headlines.append({
                'title': title,
                'url': link,
                'source': source_name,
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            })
    return headlines

sources = [
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'),
    ('BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Reuters World', 'https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US&ceid=US:en'),
    ('AP World', 'https://apnews.com/rss/headlines'),
    ('Fox News World', 'http://feeds.foxnews.com/foxnews/world'),
    ('Al Jazeera World', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('NYTimes World', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('NBC World', 'https://feeds.nbcnews.com/nbcnews/public/feeds/worldnews.rss'),
    ('The Guardian World', 'https://www.theguardian.com/world/rss'),
    ('Bloomberg World', 'https://www.bloomberg.com/feed/podcast/worldwide'),
]

all_headlines = []
for name, url in sources:
    try:
        data = fetch(url)
        heads = parse_rss(data, name)
        all_headlines.extend(heads)
    except Exception as e:
        print(f'Error fetching {name}: {e}')

# deduplicate by title
unique = {h['title']: h for h in all_headlines}
result = list(unique.values())
result.sort(key=lambda x: x['timestamp'], reverse=True)

if len(result) < 100:
    print(f'Warning: only collected {len(result)} headlines')

out_path = 'headlines.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'Saved {len(result)} headlines to {out_path}')
