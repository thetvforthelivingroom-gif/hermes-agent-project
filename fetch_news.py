import json, urllib.request, xml.etree.ElementTree as ET, datetime, os
from error_logging import log_error
from config_loader import load_config

cfg = load_config()

def fetch_rss(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read()
    except Exception as e:
        log_error('fetch_rss', -1, str(e))
        return b''

def parse_items(xml_bytes, source_name):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        log_error('parse_items', -1, str(e))
        return items
    for item in root.findall('.//item'):
        title = item.findtext('title') or ''
        link = item.findtext('link') or ''
        pub = item.findtext('pubDate')
        if pub:
            try:
                dt = datetime.datetime.strptime(pub, '%a, %d %b %Y %H:%M:%S %Z')
                pub_iso = dt.isoformat() + 'Z'
            except Exception:
                pub_iso = pub
        else:
            pub_iso = ''
        items.append({
            'title': title.strip(),
            'url': link.strip(),
            'source': source_name,
            'published_at': pub_iso
        })
    return items

feeds = [
    ("https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", "Google News US"),
    ("https://news.google.com/rss/headlines/section/topic/TECH?hl=en-US&gl=US&ceid=US:en", "Google News Tech"),
    ("https://news.google.com/rss/headlines/section/world?hl=en-US&gl=US&ceid=US:en", "Google News World")
]
all_items = []
for url, src in feeds:
    data = fetch_rss(url)
    if data:
        all_items.extend(parse_items(data, src))
# Deduplicate by URL
unique = {it['url']: it for it in all_items if it.get('url')}
items = list(unique.values())
# Sort by published_at descending (ISO format if available)
def sort_key(it):
    try:
        return datetime.datetime.fromisoformat(it['published_at'].replace('Z',''))
    except Exception:
        return datetime.datetime.min
items.sort(key=sort_key, reverse=True)
# Take top based on config max_articles
max_articles = cfg.get('max_articles', 10)
top = items[:max_articles]
output_path = os.path.join(os.getcwd(), 'stories.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(top, f, ensure_ascii=False, indent=2)
print('Wrote', len(top), 'stories to', output_path)