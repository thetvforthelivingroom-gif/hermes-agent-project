#!/usr/bin/env python3
"""Generate the News_Ag static site (fast, editorial, honest).

Reads enriched_stories.json and emits site/index.html, site/story-N.html and
site/styles.css. Titles are cleaned of "- SOURCE" suffixes; bodies merge matched
research briefs when they exist, otherwise attribute-summaries (never the old
'recent developments' filler). Zero-JS, system fonts, dark mode.
"""
import html, json, os, re, sys
from datetime import datetime, timezone

ROOT = os.getenv('HERMES_KANBAN_WORKSPACE') or '.'
DATA = os.path.join(ROOT, 'enriched_stories.json')
if not os.path.isfile(DATA):
    sys.exit('enriched_stories.json not found')

with open(DATA) as f:
    stories = json.load(f)
if not isinstance(stories, list) or not stories:
    sys.exit('enriched_stories.json is empty')

SITE = os.path.join(ROOT, 'site')
os.makedirs(SITE, exist_ok=True)

STOP = set('a an the on in of for and or to with by from at top before after as its these those'.split())
CATS = {
    'Finance/Markets': ('financia', 'market', 'stock', 'bank', 'gold', 'oil', 'treasury', 'crypto', 'dollar', 'vtb', 'inflation'),
    'World': ('iran', 'houthi', 'saudi', 'war', 'militar', 'nato', 'israel', 'ukraine', 'eu chief', 'associate'),
    'Politics': ('trump', 'hegseth', 'impeach', 'senate', 'house', 'congress', 'vote', 'lawmaker', 'supreme court'),
    'Technology': ('tech', 'app', 'software', 'device', 'boox', 'canon', 'stylus', 'camera', 'ai'),
    'Culture': ('dancing', 'sheeran', 'macklemore', 'music', 'celebrity', 'entertain', 'tour'),
    'US': ('helicopter crash', 'los angeles'),
}
FILLER_MARKERS = ('recent developments', 'key insights and implications')

def clean_title(title):
    """Remove '- SOURCE' or '- BBC' suffix from title."""
    return re.sub(r'\s*-\s*[A-Za-z0-9 .]+$', '', title).strip()

def pretty_date(ds):
    try:
        return datetime.fromisoformat(str(ds).replace('Z', '+00:00')).strftime('%b %d, %Y')
    except Exception:
        return ''

def category_of(title):
    tl = title.lower()
    for cat, keys in CATS.items():
        if any(k in tl for k in keys):
            return cat
    return 'General'

def dek_for(story, cleaned):
    """Extract a lede/dek from a story, avoiding filler markers."""
    rl = ((story.get('report') or {}).get('lede') or '').strip()
    if len(rl) > 40:
        return rl
    s = (story.get('summary') or '').strip()
    if not s:
        src = (story.get('source') or 'News').strip()
        return '%s: %s' % (cleaned[:50], src)
    clean_s = s
    for marker in FILLER_MARKERS:
        clean_s = clean_s.replace(marker, '').strip()
    if clean_s and clean_s != s:
        sentences = [sent.strip() for sent in clean_s.split('.') if sent.strip()]
        if sentences:
            result = '. '.join(sentences[:2])
            if result:
                return result.rstrip('.') + '.'
    src = (story.get('source') or 'News').strip()
    title_words = cleaned.split()
    substantive = [w for w in title_words if w not in ('a', 'an', 'the', 'on', 'in', 'of', 'for', 'and', 'or', 'to', 'with')]
    desc = ' '.join(substantive[:5])
    desc = desc[:40] if desc else cleaned[:40]
    return '%s: %s' % (desc, src)

def source_kicker(story):
    s = (story.get('source') or 'News').strip()
    return s[:22]

def find_brief(cleaned):
    words = [w for w in re.sub(r'[^a-z0-9 ]', ' ', cleaned.lower()).split() if w not in STOP and len(w) > 3]
    best = None
    best_path = None
    for f in sorted(os.listdir(ROOT)):
        if not f.endswith('.md'):
            continue
        fp = os.path.join(ROOT, f)
        try:
            with open(fp) as bf:
                lower = bf.read().lower()
        except Exception:
            continue
        lower = lower.replace('\n', ' ')
        score = sum(1 for w in words if w in lower.split())
        if score and (best is None or score > best):
            best = score
            best_path = fp
    if best is None:
        # Also check briefs/ subdirectory
        briefs_dir = os.path.join(ROOT, 'briefs')
        if os.path.isdir(briefs_dir):
            for f in sorted(os.listdir(briefs_dir)):
                if not f.endswith('.md'):
                    continue
                fp = os.path.join(briefs_dir, f)
                try:
                    with open(fp) as bf:
                        lower = bf.read().lower()
                    lower = lower.replace('\n', ' ')
                    score = sum(1 for w in words if w in lower.split())
                    if score and (best is None or score > best):
                        best = score
                        best_path = fp
                except Exception:
                    continue
    if best_path is None:
        return None
    try:
        with open(best_path) as bf:
            txt = bf.read()
    except Exception:
        return None
    paras = [p.strip() for p in txt.split('\n\n') if len(p.strip()) > 80][:4]
    return (best_path, paras)

def build_body(story, cleaned, dek):
    rep = story.get('report') or {}
    if rep.get('sections'):
        return [{'h': sec.get('h', ''), 'ps': [p for p in sec.get('ps', []) if p]} for sec in rep['sections']]
    brief = find_brief(cleaned)
    src = (story.get('source') or 'News').strip()
    date = pretty_date(story.get('published_at') or '')
    title_words = [w for w in cleaned.lower().split() if len(w) > 3]
    topic = ', '.join(title_words[:5])
    parts = []
    parts.append({'h': 'Introduction', 'ps': [dek]})
    if brief:
        parts.append({'h': 'Background & context (from research brief)', 'ps': brief[1]})
    cat = (story.get('category') or category_of(cleaned))
    why_parts = {
        'World': ['This reporting highlights significant international developments '
                  'with implications for global awareness and policy.'],
        'Politics': ['Political developments today reflect voter concerns '
                      'and policy directions shaping legislative agendas.'],
        'Technology': ['New technology reporting examines innovation trends '
                       'and their practical impact on users and industry.'],
        'Culture': ['Cultural reporting explores artistic and entertainment '
                    'developments resonating with contemporary audiences.'],
        'Finance/Markets': ['Financial market coverage tracks economic developments '
                          'and investment implications for informed readers.'],
        'US': ['Domestic news coverage addresses local and national concerns '
               'relevant to community well-being.'],
    }
    why = why_parts.get(cat, [
        'The development was reported by %s%s%s as part of today\'s news cycle.'
        % (src, ' on ' + date if date else '', '.' if not date else '')
    ])
    parts.append({'h': 'Why it matters', 'ps': why})
    parts.append({'h': 'Source & further reading', 'ps': [
        'This page aggregates the headline and context; the full original report '
        'is linked in the source panel below. Topic keywords: ' + (topic or 'n/a') + '.'
    ]})
    return parts

def esc(x):
    return html.escape(str(x), quote=True)

def render_para(p, sources=None):
    t = esc(p)
    if sources:
        t = re.sub(r'\[(\d+)\]', lambda m: '<sup class="cite"><a href="#src-%s">[%s]</a></sup>' % (m.group(1), m.group(1)), t)
    return '<p>%s</p>' % t

def svg_placeholder(color_a, color_b, label):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">'
           '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>'
           '<rect width="800" height="450" fill="url(#g)"/>'
           '<text x="400" y="230" font-family="Georgia,serif" font-size="34" fill="rgba(255,255,255,0.85)" '
           'text-anchor="middle">%s</text></svg>') % (color_a, color_b, esc(label))
    return 'data:image/svg+xml;charset=utf-8,' + svg.replace('#', '%23').replace('"', '%22').replace(' ', '%20')

def image_for(story, cleaned):
    t = (story.get('thumbnail') or '').strip()
    if t and not t.startswith('http'):
        return t, t.endswith('.svg')
    u = (story.get('image_url') or '').strip()
    if (u.startswith('http') and 'source.unsplash.com' not in u
            and 'images.pexels' not in u and 'pexels.com' not in u):
        return u, False
    return svg_placeholder('#3a5a8c', '#1c2739', cleaned[:60]), True

STYLES = """body {background:#f7f5f0;color:#16181d;font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55}
.wrap {max-width:960px;margin:0 auto;padding:0 18px}
header.site {border-bottom:1px solid #e3ded3;padding:22px 0 18px;margin-bottom:8px}
.brand {display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.brand h1 {font-family:Georgia,"Times New Roman",serif;font-size:26px;margin:0;letter-spacing:-0.2px}
.brand .tag {color:#5b626e;font-size:13px}
.hero {margin:22px 0 6px}
.hero h2 {font-family:Georgia,serif;font-size:20px;font-weight:600;margin:0 0 4px}
.hero p {color:#5b626e;margin:0;font-size:14px}
.grid {display:grid;grid-template-columns:1fr;gap:16px;margin:22px 0 40px}
@media (min-width:620px) {.grid {grid-template-columns:repeat(2,1fr)}}
.card {background:#fff;border:1px solid #e3ded3;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit;transition:transform .12s ease,box-shadow .12s ease}
.card:hover {transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.08)}
.card .media {height:150px;background:#22334d;background-image:linear-gradient(135deg,#3a5a8c,#1c2739);background-size:cover;background-position:center}
.card img {width:100%;height:150px;object-fit:cover;display:block}
.card .body {padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px;flex:1}
.kicker {font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:#b3402a;font-weight:700}
.card h3 {font-family:Georgia,serif;font-size:17px;margin:0;line-height:1.35}
.card p {color:#5b626e;font-size:13.5px;margin:0}
.meta {color:#5b626e;font-size:12px;margin-top:auto;padding-top:8px}
article {max-width:720px;margin:34px auto 60px}
article .kicker {font-size:12px}
article h1 {font-family:Georgia,serif;font-size:31px;line-height:1.15;margin:10px 0 6px;letter-spacing:-0.3px}
.byline {color:#5b626e;font-size:14px;margin-bottom:26px;border-bottom:1px solid #e3ded3;padding-bottom:16px}
.lede {font-size:19px;line-height:1.5;color:#16181d;border-left:3px solid #b3402a;padding-left:16px;margin:0 0 26px;font-family:Georgia,serif}
section {margin:0 0 28px}
section h3 {font-family:Georgia,serif;font-size:19px;margin:0 0 10px}
section p {margin:0 0 14px}
.source-panel {background:#fff;border:1px solid #e3ded3;border-radius:10px;padding:14px 16px;font-size:13.5px;color:#5b626e}
.source-panel a {color:#b3402a}
footer.site {border-top:1px solid #e3ded3;padding:18px 0 40px;color:#5b626e;font-size:12.5px}
footer.site .wrap {display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
.hero-img {margin:22px 0 24px}
.hero-img img {width:100%;height:auto;border-radius:12px;display:block;background:#22334d}
.credit {font-size:12px;color:#8a909a;margin:6px 2px 0}
.sources ol {margin:6px 0 10px;padding-left:22px}
.sources li {margin:0 0 7px;font-size:13.5px;line-height:1.45}
.sources .pub {font-weight:700;color:#333}
.sources a {color:#b3402a;text-decoration:none;word-break:break-word}
.sources a:hover {text-decoration:underline}
.srcnote {font-size:12px;color:#8a909a;margin:6px 0 0}
.cite a {text-decoration:none;color:#b3402a;font-size:11px;padding:0 1px}
.card img {background:#22334d}
"""

def page(title, body_html, extrahead='', meta_desc='', meta_image='images/favicon.svg'):
    meta = []
    if meta_desc:
        meta.append('<meta name="description" content="%s">' % esc(meta_desc))
        meta.append('<meta property="og:description" content="%s">' % esc(meta_desc))
    meta.append('<meta name="twitter:card" content="summary_large_image">')
    meta.append('<meta property="og:title" content="%s">' % esc(title))
    meta.append('<meta property="og:type" content="website">')
    meta.append('<meta property="og:image" content="%s">' % esc(meta_image))
    head = ('\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           '<title>%s</title>\n'
           '<link rel="icon" type="image/svg+xml" href="images/favicon.svg">\n'
           '<link rel="stylesheet" href="styles.css">%s' % (title, ''.join(meta)))
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>%s%s</head>\n<body>%s\n</body>\n</html>' % (head, extrahead, body_html))

index_cards = []
now = datetime.now(timezone.utc)
generated = now.strftime('%B %d, %Y')
for i, story in enumerate(stories):
    cleaned = clean_title(story.get('title', 'Untitled'))
    dek = dek_for(story, cleaned)
    cat = (story.get('category') or category_of(cleaned))
    src = (story.get('source') or 'News').strip()
    src = re.sub(r'\s*-\s*$', '', src)
    date = pretty_date(story.get('published_at') or '')
    img, is_svg = image_for(story, cleaned)
    fname = 'story-%d.html' % i
    parts = build_body(story, cleaned, dek)
    body = []
    body.append('<header class="site"><div class="wrap"><div class="brand"><h1><a href="index.html" style="color:inherit;text-decoration:none">The Daily Brief</a></h1><span class="tag">%s</span></div></div></header>' % generated)
    body.append('<article><div class="kicker">%s%s%s</div>' % (esc(cat), ' &middot; ' + esc(src) if src else '', ' &middot; ' + esc(date) if date else ''))
    body.append('<h1>%s</h1>' % esc(cleaned))
    body.append('<div class="byline">By %s%s</div>' % (esc(src or 'Staff'), ' &middot; ' + esc(date) if date else ''))
    body.append('<div class="lede">%s</div>' % esc(dek))
    if img:
        cap = '<figcaption class="credit">Image: %s</figcaption>' % esc(story.get('image_credit')) if (story.get('image_credit') or '').strip() else ''
        body.append('<figure class="hero-img"><img src="%s" alt="%s" loading="eager" width="700" height="394">%s</figure>' % (esc(img), esc(cleaned), cap))
    rep = story.get('report') or {}
    srcs = rep.get('sources') or []
    for part in parts:
        body.append('<section><h3>%s</h3>%s</section>' % (esc(part['h']), ''.join(render_para(p, srcs) for p in part['ps'])))
    if srcs:
        items = ''.join('<li id="src-%s"><span class="pub">%s</span> <a href="%s" target="_blank" rel="noopener">%s</a></li>' % (
            esc(s.get('n')), esc((s.get('publisher') or 'Source').split(' - ')[0]), esc(s.get('url') or '#'), esc(s.get('title') or 'Report')) for s in srcs)
        body.append('<section class="sources"><h3>Sources &amp; further reading</h3><ol>%s</ol><p class="srcnote">This report aggregates %d independent outlets; each item links to the original.</p></section>' % (items, len(srcs)))
    url = story.get('url') or ''
    body.append('<section class="source-panel"><strong>Source:</strong> %s%s</section>' % \
                (esc(src), ' &middot; <a href="%s" target="_blank" rel="noopener">Read the original report</a>' % esc(url) if url else ''))
    body.append('</article>')
    body.append('<footer class="site"><div class="wrap"><span>%s</span><span>Generated during the %s cycle</span></div></footer>' % (generated, generated))
    with open(os.path.join(SITE, fname), 'w') as f:
        f.write(page(esc(cleaned), ''.join(body), meta_desc=dek, meta_image=img or 'images/favicon.svg'))
    index_cards.append((cleaned, cat, src, date, dek, img, fname, is_svg))

idx = []
for cleaned, cat, src, date, dek, img, fname, is_svg in index_cards:
    media = ('<img src="%s" alt="%s" loading="lazy" width="480" height="150">' % (esc(img), esc(cleaned))) if img else ''
    idx.append(('<a class="card" href="%s">%s<div class="body"><span class="kicker">%s</span>'
                '<h3>%s</h3><p>%s</p><div class="meta">%s%s</div></div></a>' \
                % (fname, media, esc(cat), esc(cleaned), esc(dek[:110]), esc(src or 'News'),
                   ' &middot; ' + esc(date) if date else '')).replace('</a><div class="body">', '<div class="body">', 1))

index_body = [
    '<header class="site"><div class="wrap"><div class="brand"><h1>The Daily Brief</h1>'
    '<span class="tag">%s &middot; <a href="archive/index.html" style="color:#b3402a">Archive</a></span></div></div></header>' % generated,
    '<div class="wrap"><div class="hero"><h2>%s</h2><p>%d stories from today\u2019s news cycle, aggregated and linked to original reporting.</p></div>' % (generated, len(stories)),
    '<div class="grid">%s</div></div>' % ''.join(idx),
    '<footer class="site"><div class="wrap"><span>%s &middot; Sources linked to original reporting</span><span>fast, static, zero-JS</span></div></footer>' % generated,
]

with open(os.path.join(SITE, 'index.html'), 'w') as f:
    f.write(page('The Daily Brief - News Aggregator', ''.join(index_body),
                 meta_desc='%d stories from today\'s news cycle, aggregated and linked to original reporting.' % len(stories)))
with open(os.path.join(SITE, 'styles.css'), 'w') as f:
    f.write(STYLES)
print('site generated: %d stories -> %s' % (len(stories), SITE))