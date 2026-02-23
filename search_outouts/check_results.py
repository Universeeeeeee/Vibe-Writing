"""快速查看候选池效果"""
import requests

resp = requests.get('http://localhost:8000/api/candidates?page_size=15')
data = resp.json()
print(f"候选总数: {data['total']}\n")
print("前15篇（按 system_score 降序）:")
print("-" * 80)

for i, p in enumerate(data['items']):
    score = p.get('system_score', 0)
    tags = p.get('tags', [])
    app = "🔴APP" if p.get('app_heavy') else ""
    src = p.get('retrieval_source', '')[:3]
    title = p['title'][:55]
    print(f"{i+1:2}. [{src}] score={score:+.1f} {app:6} tags={tags}")
    print(f"    {title}...")
