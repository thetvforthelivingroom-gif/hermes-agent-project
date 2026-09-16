import json, urllib.parse, os

input_path = '/home/sparky/News_Ag/stories.json'
output_path = '/home/sparky/News_Ag/enriched_stories.json'

with open(input_path, 'r') as f:
    stories = json.load(f)

enriched = []
for story in stories:
    title = story.get('title', '')
    # Placeholder summary: 2-3 sentences about the article
    summary = f"This article titled '{title}' reports recent developments in its respective field. It provides key insights and implications for readers."
    # Unsplash source URL with title keywords
    query = urllib.parse.quote_plus(title)
    image_url = f"https://source.unsplash.com/featured/800x600?{query}"
    story_enriched = dict(story)
    story_enriched['summary'] = summary
    story_enriched['image_url'] = image_url
    enriched.append(story_enriched)

with open(output_path, 'w') as f:
    json.dump(enriched, f, indent=2)

print('Created', output_path, 'with', len(enriched), 'entries')
