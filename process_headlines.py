import json, re, sys

with open('headlines.json') as f:
    data = json.load(f)

source_weights = {
    'The Guardian World': 0.9,
    'Guardian World': 0.9,
    'NYTimes World': 1.0,
    'Reuters World': 1.0,
    'Al Jazeera World': 0.8,
    'Fox News World': 0.6,
    'BBC World': 0.7,
    'CNN World': 0.5,
}
keywords = ['AI','inflation','oil','war','Russia','China','Iran','Houthi','Trump','Biden','election','stock','market','crypto','technology','climate','environment','sports','energy']

def source_weight(src):
    return source_weights.get(src, 0.4)

ranked = []
for entry in data:
    title = entry.get('title','')
    src = entry.get('source','')
    kw = sum(1 for kw in keywords if re.search(r'(?i)\\b'+re.escape(kw)+r'\\b', title))
    score = source_weight(src) + 0.1*kw
    ranked.append({
        'headline': title,
        'source': src,
        'url': entry.get('url',''),
        'relevance_score': round(score,3)
    })

ranked.sort(key=lambda x: (x['relevance_score'], len(x['headline'])), reverse=True)

top10 = ranked[:10]
with open('top_headlines.json','w') as out:
    json.dump(top10, out, indent=2)
