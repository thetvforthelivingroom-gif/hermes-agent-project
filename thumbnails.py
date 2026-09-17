#!/usr/bin/env python3
"""Resolve a thumbnail per story, best-source-first, cached locally so the site
stays fast (zero external requests at view time).

Tiers: 1) publisher og:image (direct URLs only)  2) Wikipedia/Wikimedia Commons
       3) locally-generated category SVG banner (always works).
Writes back enriched_stories.json: thumbnail (relative), image_credit, category.
"""
import concurrent.futures as cf, json, os, re, shutil, urllib.parse, urllib.request
from io import BytesIO

ROOT = '/home/sparky/News_Ag'
SITE = os.path.join(ROOT, 'site')
IMG = os.path.join(SITE, 'images')
os.makedirs(IMG, exist_ok=True)
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
DATA = os.path.join(ROOT, 'enriched_stories.json')

CATS = [
    ('Politics', ('trump', 'hegseth', 'impeach', 'senate', 'house', 'congress', 'vote', 'lawmaker', 'supreme court', 'election', 'ballot', 'shutdown', 'white house', 'president')),
    ('World', ('iran', 'iowa', 'houthi', 'saudi', 'mecca', 'war', 'militar', 'nato', 'israel', 'ukraine', 'canada', 'eu chief', 'china', 'russia', 'sanction', 'vtb', 'pentagon', 'helicopter', 'los angeles')),
    ('Business', ('financia', 'market', 'stock', 'bank', 'gold', 'oil', 'treasury', 'crypto', 'dollar', 'inflation', 'economy', 'equity', 'ipo', 'bitcoin')),
    ('Science', ('nasa', 'space', 'climate', 'study', 'researchers', 'physics', 'biolog', 'rocket', 'asteroid', 'discovery', 'scientist')),
    ('Health', ('health', 'medical', 'hospital', 'disease', 'vaccine', 'cancer', 'doctor', 'mental', 'virus', 'fda')),
    ('Pets', ('dog', 'cat', 'pet', 'puppy', 'kitten', 'animal', 'vet ', 'shelter', 'wildlife')),
    ('Cooking', ('recipe', 'cook', 'food', 'chef', 'restaurant', 'meal', 'baking', 'kitchen', 'cuisine')),
    ('Lifestyle', ('travel', 'fashion', 'garden', 'wellness', 'mindful', 'habit', 'beauty', 'home decor')),
    ('Culture', ('dancing', 'sheeran', 'macklemore', 'music', 'celebrity', 'entertain', 'tour', 'film', 'movie', 'album', 'actor', 'premiere', 'season 3')),
    ('Sports', ('seahawks', 'nfl', 'nba', 'mlb', 'soccer', 'olympic', 'match', 'tournament', 'coach', 'league', 'season', 'playoff')),
    ('Technology', ('tech', ' app', 'software', 'device', 'boox', 'canon', 'stylus', 'camera', 'chip', 'phone', 'gadget', 'ai ', 'robot', 'laptop')),
    ('News', ()),
]
GLYPH = {
    'Politics': '<path d="M24 6 4 17h40L24 6z"/><rect x="8" y="20" width="5" height="16"/><rect x="21" y="20" width="5" height="16"/><rect x="34" y="20" width="5" height="16"/><rect x="4" y="38" width="40" height="4"/>',
    'World': '<circle cx="24" cy="24" r="17" fill="none" stroke-width="3"/><path d="M7 24h34M24 7c7 7 7 27 0 34M24 7c-7 7-7 27 0 34" fill="none" stroke-width="3"/>',
    'Business': '<rect x="8" y="26" width="7" height="16"/><rect x="20" y="18" width="7" height="24"/><rect x="32" y="10" width="7" height="32"/><rect x="4" y="42" width="40" height="3"/>',
    'Science': '<path d="M20 4h8v13l10 20a4 4 0 0 1-4 6H14a4 4 0 0 1-4-6l10-20V4z"/><path d="M16 4h16" stroke-width="3"/>',
    'Sports': '<circle cx="24" cy="24" r="17" fill="none" stroke-width="3"/><path d="M24 7v34M7 24h34M12 12c7 5 17 5 24 0M12 36c7-5 17-5 24 0" fill="none" stroke-width="3"/>',
    'Health': '<path d="M18 4h12v14h14v12H30v14H18V30H4V18h14z"/>',
    'Pets': '<circle cx="14" cy="14" r="5"/><circle cx="34" cy="14" r="5"/><circle cx="6" cy="27" r="4"/><circle cx="42" cy="27" r="4"/><path d="M24 20c8 0 14 6 14 13 0 6-6 9-14 9s-14-3-14-9c0-7 6-13 14-13z"/>',
    'Cooking': '<path d="M8 20h32v8a16 16 0 0 1-32 0v-8z"/><path d="M4 20h40M16 10c0-4 4-4 4-8M28 10c0-4 4-4 4-8" stroke-width="3" fill="none"/>',
    'Lifestyle': '<path d="M24 44C10 34 6 24 12 16c5-7 14-4 12 4-2-8 7-11 12-4 6 8 2 18-12 28z"/>',
    'Culture': '<rect x="8" y="10" width="32" height="28" rx="3" fill="none" stroke-width="3"/><path d="M8 18h32M15 6l5 4M33 6l-5 4" stroke-width="3"/><circle cx="18" cy="30" r="3"/><circle cx="30" cy="30" r="3"/>',
    'Technology': '<rect x="13" y="13" width="22" height="22" rx="3" fill="none" stroke-width="3"/><rect x="20" y="20" width="8" height="8"/><path d="M19 5v6M29 5v6M19 37v6M29 37v6M5 19h6M5 29h6M37 19h6M37 29h6" stroke-width="3"/>',
    'News': '<rect x="7" y="7" width="34" height="36" rx="3" fill="none" stroke-width="3"/><path d="M13 15h22M13 23h22M13 31h14" stroke-width="3"/>',
}

def category_of(title):
    tl = ' ' + title.lower() + ' '
    for cat, keys in CATS:
        if keys and any(k in tl for k in keys):
            return cat
    return 'News'

def write_icon(cat):
    rel = 'images/cat-%s.svg' % cat.lower().replace(' ', '-')
    dest = os.path.join(SITE, rel)
    glyph = GLYPH.get(cat, GLYPH['News'])
    label = cat.upper()
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 150" width="480" height="150" role="img">'
           '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="#3c5d8f"/><stop offset="1" stop-color="#131b2a"/></linearGradient></defs>'
           '<rect width="480" height="150" fill="url(#g)"/>'
           '<g transform="translate(28,35) scale(1.7)" fill="#e9eff8" stroke="#e9eff8" stroke-linejoin="round" opacity="0.92">'
           + glyph + '</g>'
           '<text x="452" y="139" text-anchor="end" font-family="Georgia,serif" font-size="15" '
           'letter-spacing="3" fill="rgba(233,239,248,0.62)">' + label + '</text></svg>')
    with open(dest, 'w') as f:
        f.write(svg)
    return rel

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def og_image(url):
    """Extract og:image from a URL. If URL is a Google News wrapper, resolve to original publisher first."""
    # If this is a Google News URL, extract the original publisher URL from query params
    if 'news.google.com' in url:
        parts = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parts.query)
        # Google News uses 'url' or 'u' parameter for the original article URL
        orig = query.get('url') or query.get('u')
        if orig:
            url = urllib.parse.unquote(orig[0])
        else:
            # If we can't extract, fall through to try fetching the Google News page directly
            pass
    
    try:
        html = fetch(url).decode('utf-8', 'replace')
    except Exception:
        return None
    
    for pat in (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'):
        m = re.search(pat, html, re.I)
        if m and m.group(1).startswith('http'):
            return m.group(1)
    return None

def wiki_image(title):
    queries = [title]
    words = [w for w in re.findall(r"[A-Za-z0-9']+", title) if len(w) > 3][:5]
    if words:
        queries.append(' '.join(words[:4]))
    for q in queries:
        api = ('https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages'
               '&piprop=thumbnail&pithumbsize=640&generator=search&gsrsearch='
               + urllib.parse.quote(q) + '&gsrlimit=1')
        try:
            d = json.loads(fetch(api))
            for p in ((d.get('query') or {}).get('pages') or {}).values():
                src = (p.get('thumbnail') or {}).get('source')
                if src:
                    return src
        except Exception:
            pass
    return None

def api_keys():
    """Stock-photo API keys, from env first, then hermes config.yaml."""
    pexels = os.environ.get('PEXELS', '')
    unsplash = os.environ.get('UNSPLASH_ACCESS', '')
    if pexels and unsplash:
        return pexels, unsplash
    cfg = os.path.expanduser('~/.hermes/config.yaml')
    try:
        with open(cfg) as f:
            for line in f:
                line = line.strip()
                if line.startswith('PEXELS:') and not pexels:
                    pexels = line.split(':', 1)[1].strip()
                elif line.startswith('UNSPLASH_ACCESS:') and not unsplash:
                    unsplash = line.split(':', 1)[1].strip()
    except Exception:
        pass
    return pexels, unsplash

def stock_image(title):
    """Best-fit stock photo (Pexels -> Unsplash) for a story title. Returns (url, credit) or (None, '')."""
    pexels_key, unsplash_key = api_keys()
    stop = set('a an the on in of for and or to with by from at top before after as its these those'.split())
    words = [w for w in re.sub(r'[^A-Za-z]+', ' ', title.lower()).split() if w not in stop and len(w) > 3]
    query = ' '.join(words[:4]) or title
    try:
        req = urllib.request.Request(
            'https://api.pexels.com/v1/search?query=%s&per_page=3&orientation=landscape' % urllib.parse.quote(query),
            headers={'Authorization': pexels_key, 'Accept': '*/*', 'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read().decode('utf-8'))
        photos = d.get('photos') or []
        if photos:
            p = photos[0]
            src = ((p.get('src') or {}).get('large2x')
                   or (p.get('src') or {}).get('large')
                   or (p.get('src') or {}).get('original'))
            if src:
                return src, 'Photo by %s on Pexels' % (p.get('photographer') or 'Pexels')
    except Exception:
        pass
    try:
        req = urllib.request.Request(
            'https://api.unsplash.com/search/photos?query=%s&per_page=3&orientation=landscape' % urllib.parse.quote(query),
            headers={'Authorization': 'Client-ID ' + unsplash_key, 'Accept': '*/*', 'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read().decode('utf-8'))
        results = d.get('results') or []
        if results:
            res = results[0]
            src = ((res.get('urls') or {}).get('regular')
                   or (res.get('urls') or {}).get('raw'))
            if src:
                user = ((res.get('user') or {}).get('name')) or 'Unsplash'
                return src, 'Photo by %s on Unsplash' % user
    except Exception:
        pass
    return None, ''

def save_image(data, stem):
    if b'<svg' in data[:400].lower():
        rel = 'images/%s.svg' % stem
        with open(os.path.join(SITE, rel), 'wb') as f:
            f.write(data)
        return rel
    try:
        from PIL import Image
        im = Image.open(BytesIO(data)).convert('RGB')
        im.thumbnail((700, 700))
        if im.width < 220:
            return None
        rel = 'images/%s.webp' % stem
        im.save(os.path.join(SITE, rel), 'WEBP', quality=72, method=5)
        return rel
    except Exception:
        return None

def process(i, story):
    title = re.sub(r'\s*-\s*[A-Za-z0-9 .\']+$', '', (story.get('title') or '')).strip()
    cat = category_of(title)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:38].strip('-') or ('story-%d' % i)
    stem = '%02d-%s' % (i, slug)
    
    # Try to get og:image from the FIRST SOURCE URL (original publisher), not the Google News wrapper URL
    source_url = ''
    sources = story.get('sources') or []
    if sources:
        source_url = sources[0].get('url', '')
    
    img = og_image(source_url) if source_url else ''
    if img:
        try:
            rel = save_image(fetch(img), stem)
            if rel:
                return i, rel, (sources[0].get('publisher') or story.get('source') or '').strip(), cat, 'og'
        except Exception:
            pass
    
    # Fallback to Wikipedia/Wikimedia Commons
    wimg = wiki_image(title)
    if wimg:
        try:
            rel = save_image(fetch(wimg), stem + '-wiki')
            if rel:
                return i, rel, 'Wikimedia Commons', cat, 'wiki'
        except Exception:
            pass
    
    # Fallback to a relevant stock photo (Pexels/Unsplash) with photographer credit
    surl, scredit = stock_image(title)
    if surl:
        try:
            rel = save_image(fetch(surl, timeout=20), stem + '-stock')
            if rel:
                return i, rel, scredit, cat, 'stock'
        except Exception:
            pass
    
    # Final fallback: category icon
    return i, write_icon(cat), '', cat, 'icon'

def main():
    with open(DATA) as f:
        stories = json.load(f)
    shutil.copy(DATA, DATA + '.bak')
    results, tiers = {}, {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for fut in cf.as_completed([ex.submit(process, i, s) for i, s in enumerate(stories)]):
            try:
                i, rel, credit, cat, tier = fut.result()
                results[i] = (rel, credit, cat)
                tiers[tier] = tiers.get(tier, 0) + 1
            except Exception as e:
                print('worker error:', e)
    for i, s in enumerate(stories):
        rel, credit, cat = results.get(i, (write_icon('News'), '', 'News'))
        s['thumbnail'] = rel
        s['image_credit'] = credit
        s['category'] = cat
        print('  [%-4s] %-58s -> %s' % (cat, (s.get('title') or '')[:56], rel))
    with open(DATA, 'w') as f:
        json.dump(stories, f, indent=2)
    print('tiers: %s' % tiers)

if __name__ == '__main__':
    main()
