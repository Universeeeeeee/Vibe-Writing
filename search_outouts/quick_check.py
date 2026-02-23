import requests
r = requests.get('http://localhost:8000/api/candidates?page_size=10')
d = r.json()
print('Total:', d['total'])
for i, p in enumerate(d['items']):
    score = p.get('system_score', 0)
    tags = p.get('tags', [])
    title = p['title'][:45]
    print(f"{i+1:2}. score={score:+.0f} tags={tags} - {title}...")
