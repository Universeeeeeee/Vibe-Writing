"""验证排序逻辑"""
import requests

r = requests.get('http://localhost:8000/api/candidates?page_size=10')
data = r.json()['items']
print('排序验证 (按 retrieval_score 降序，同分按 rank 升序):')
for i, p in enumerate(data):
    print(f"  {i+1}. score={p.get('retrieval_score')}, rank={p.get('rank')}, title={p['title'][:45]}...")
