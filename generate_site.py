import json, os, re, html, sys
workspace = os.getenv('HERMES_KANBAN_WORKSPACE') or '.'
json_path = os.path.join(workspace, 'enriched_stories.json')
if not os.path.isfile(json_path):
    print('enriched_stories.json not found', file=sys.stderr)
    sys.exit(1)
with open(json_path, 'r') as f:
    data = json.load(f)
site_dir = os.path.join(workspace, 'site')
os.makedirs(site_dir, exist_ok=True)

def safe_slug(text):
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug)
    return slug[:50].strip('-')

story_filenames = []
for i, story in enumerate(data):
    filename = f"story-{i}.html"
    story_filenames.append((filename, story))
    title = html.escape(story.get('title', 'Untitled'))
    summary = html.escape(story.get('summary', ''))
    source_url = story.get('url', '#')
    image_url = story.get('image_url', '')
    html_content = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<title>{title}</title>
<style>
body{{font-family:Arial,sans-serif;margin:20px;max-width:800px;}}
img{{max-width:100%;height:auto;}}
.container{{margin-bottom:20px;}}
</style>
</head>
<body>
<div class='container'>
<h1>{title}</h1>
<img src='{html.escape(image_url)}' alt='Image'>
<p>{summary}</p>
<p>Source: <a href='{html.escape(source_url)}' target='_blank'>Read original</a></p>
</div>
</body>
</html>"""
    with open(os.path.join(site_dir, filename), 'w') as f:
        f.write(html_content)

index_items = []
for filename, story in story_filenames:
    title = html.escape(story.get('title', 'Untitled'))
    thumb = html.escape(story.get('image_url', ''))
    link = filename
    index_items.append(f"<div class='item'><a href='{link}'><img src='{thumb}' alt='thumb'><h2>{title}</h2></a></div>")
index_html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<title>News Site</title>
<style>
body{{font-family:Arial,sans-serif; margin:20px;}}
.item{{margin-bottom:20px;}}
.item img{{width:200px;height:auto;float:left;margin-right:10px;}}
.item h2{{margin:0;}}
.clearfix::after{{content:'';clear:both;display:table;}}
</style>
</head>
<body>
<h1>News Stories</h1>
<div class='list'>
{''.join(index_items)}
<div class='clearfix'></div>
</div>
</body>
</html>"""
with open(os.path.join(site_dir, 'index.html'), 'w') as f:
    f.write(index_html)
print('Site generated at', site_dir)
