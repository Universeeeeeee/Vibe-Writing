"""
端到端验证：测试宽松版检索策略
"""
import requests
import json

API_BASE = "http://localhost:8000/api"

print("=" * 60)
print("宽松版检索策略端到端验证")
print("=" * 60)

# 1. 检查现有数据
print("\n【1】检查现有候选数量...")
resp = requests.get(f"{API_BASE}/candidates?page_size=5")
data = resp.json()
print(f"  当前候选总数: {data['total']}")

# 2. 刷新候选池（获取新论文）
print("\n【2】刷新候选池...")
resp = requests.post(f"{API_BASE}/candidates/refresh", json={
    "max_results": 5,
    "sources": ["arxiv", "pubmed"]
})
result = resp.json()
print(f"  新增: {result.get('added', 0)} 篇")
print(f"  检索量: {result.get('total_retrieved', 0)} 篇")
print(f"  按来源: {result.get('by_source', {})}")

# 3. 验证新字段
print("\n【3】验证新字段...")
resp = requests.get(f"{API_BASE}/candidates?page_size=10")
data = resp.json()
items = data['items']

if items:
    print(f"\n  前 {len(items)} 篇候选论文:")
    for i, p in enumerate(items):
        tags = p.get('tags', [])
        system_score = p.get('system_score', 0)
        app_heavy = p.get('app_heavy', False)
        
        print(f"\n  [{i+1}] {p['title'][:50]}...")
        print(f"      system_score: {system_score}")
        print(f"      tags: {tags}")
        print(f"      app_heavy: {app_heavy}")
        print(f"      source: {p.get('retrieval_source')}")
    
    # 4. 验证排序逻辑
    print("\n【4】验证排序逻辑...")
    scores = [p.get('system_score', 0) for p in items]
    app_heavies = [p.get('app_heavy', False) for p in items]
    
    # 检查 app_heavy=false 是否在前面
    app_heavy_positions = [i for i, ah in enumerate(app_heavies) if ah]
    non_app_heavy_positions = [i for i, ah in enumerate(app_heavies) if not ah]
    
    if app_heavy_positions and non_app_heavy_positions:
        if min(app_heavy_positions) > max(non_app_heavy_positions):
            print("  ✅ app_heavy=false 的论文排在前面")
        else:
            print("  ⚠️ app_heavy 排序可能有问题")
    else:
        print("  ℹ️ 无法验证 app_heavy 排序（样本不足）")
    
    # 检查非 app_heavy 论文的 system_score 是否降序
    non_app_scores = [scores[i] for i in non_app_heavy_positions]
    if non_app_scores == sorted(non_app_scores, reverse=True):
        print("  ✅ system_score 降序排列正确")
    else:
        print(f"  ⚠️ system_score 排序: {non_app_scores}")
else:
    print("  ❌ 没有候选论文")

print("\n" + "=" * 60)
print("验证完成！")
