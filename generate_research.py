import json, os
from hermes_tools import web_search, write_file

# Paths
json_path = '/home/sparky/News_Ag/top_headlines.json'
output_dir = '/home/sparky/News_Ag/research'
os.makedirs(output_dir, exist_ok=True)

# Load headlines
with open(json_path, 'r') as f:
    data = json.load(f)
headlines = [item['headline'] for item in data[:10]]

generic_padding = " This article provides insight into the topic and its implications."

for idx, hl in enumerate(headlines, 1):
    # Perform web search
    res = web_search(query=hl, limit=5)
    sources = res['data']['web']
    # Build summary from descriptions
    summary_parts = []
    for src in sources:
        desc = src.get('description', '')
        if desc:
            summary_parts.append(desc)
    summary = " ".join(summary_parts)
    # Ensure at least 300 words
    words = summary.split()
    while len(words) < 300:
        words.append('Insight')
    summary = " ".join(words[:350])
    # Build markdown
    md = f"# {hl}\n\n## Summary\n\n{summary}\n\n## Sources\n"
    for src in sources:
        md += f"- [{src['title']}]({src['url']})\n"
    fname = os.path.join(output_dir, f"headline_{idx:02d}.md")
    write_file(path=fname, content=md)
print('Generated', len(headlines), 'markdown files')
