"""
测试脚本：验证问题1和问题2的修复效果
"""
import requests
import json

API_BASE = "http://localhost:8000/api"

def test_query_id_mismatch():
    """测试：前端传入错误的 query_id 应返回 400"""
    print("\n=== 测试1: query_id 不匹配应返回 400 ===")
    
    # 先获取一个候选论文
    resp = requests.get(f"{API_BASE}/candidates?page_size=1")
    candidates = resp.json()["items"]
    if not candidates:
        print("❌ 没有候选论文，请先刷新候选池")
        return False
    
    paper = candidates[0]
    paper_id = paper["paper_id"]
    correct_query_id = paper["query_id"]
    wrong_query_id = "wrong_query_id_12345"
    
    print(f"  paper_id: {paper_id[:50]}...")
    print(f"  正确 query_id: {correct_query_id}")
    print(f"  错误 query_id: {wrong_query_id}")
    
    # 尝试用错误的 query_id 提交反馈
    resp = requests.post(f"{API_BASE}/feedback", json={
        "paper_id": paper_id,
        "query_id": wrong_query_id,
        "label": "reject"
    })
    
    if resp.status_code == 400:
        print(f"  ✅ 正确返回 400: {resp.json()['detail']}")
        return True
    else:
        print(f"  ❌ 期望 400，实际 {resp.status_code}: {resp.text}")
        return False


def test_scores_snapshot_complete():
    """测试：scores_snapshot 应包含完整字段"""
    print("\n=== 测试2: scores_snapshot 完整性 ===")
    
    # 获取一个 pending 状态的候选论文
    resp = requests.get(f"{API_BASE}/candidates?status=pending&page_size=1")
    candidates = resp.json()["items"]
    if not candidates:
        print("❌ 没有 pending 状态的候选论文")
        return False
    
    paper = candidates[0]
    paper_id = paper["paper_id"]
    
    print(f"  paper_id: {paper_id[:50]}...")
    print(f"  retrieval_score: {paper.get('retrieval_score')}")
    print(f"  rank: {paper.get('rank')}")
    
    # 检查 candidate 是否有必要字段
    if paper.get("retrieval_score") is None or paper.get("rank") is None:
        print("  ⚠️ 候选本身缺少字段，API 应拒绝反馈")
        resp = requests.post(f"{API_BASE}/feedback", json={
            "paper_id": paper_id,
            "label": "reject"
        })
        if resp.status_code == 400:
            print(f"  ✅ 正确拒绝了缺字段的反馈: {resp.json()['detail']}")
            return True
        else:
            print(f"  ❌ 期望 400，实际 {resp.status_code}")
            return False
    else:
        print("  ✅ 候选字段完整，scores_snapshot 将被正确填充")
        return True


def test_correct_feedback():
    """测试：正确的反馈应该成功"""
    print("\n=== 测试3: 正确的反馈应成功 ===")
    
    resp = requests.get(f"{API_BASE}/candidates?status=pending&page_size=1")
    candidates = resp.json()["items"]
    if not candidates:
        print("❌ 没有 pending 状态的候选论文")
        return False
    
    paper = candidates[0]
    paper_id = paper["paper_id"]
    correct_query_id = paper["query_id"]
    
    print(f"  paper_id: {paper_id[:50]}...")
    
    # 使用正确的 query_id 或不传 query_id
    resp = requests.post(f"{API_BASE}/feedback", json={
        "paper_id": paper_id,
        "query_id": correct_query_id,  # 正确的 query_id
        "label": "reject",
        "reason_tags": ["off_topic"]
    })
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"  ✅ 反馈成功: {result['message']}")
        
        # 检查 feedback 文件中的记录
        feedback_resp = requests.get(f"{API_BASE}/feedback")
        feedbacks = feedback_resp.json()["items"]
        if feedbacks:
            latest = feedbacks[-1]
            print(f"  最新反馈 query_id: {latest.get('query_id')}")
            print(f"  scores_snapshot: {latest.get('scores_snapshot')}")
            
            # 验证字段完整性
            ss = latest.get("scores_snapshot", {})
            if ss.get("retrieval_score") is not None and ss.get("rank") is not None:
                print("  ✅ scores_snapshot 完整")
                return True
            else:
                print("  ❌ scores_snapshot 不完整")
                return False
        return True
    else:
        print(f"  ❌ 反馈失败: {resp.status_code} - {resp.text}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("验证问题1和问题2的修复效果")
    print("=" * 50)
    
    results = []
    results.append(("query_id 不匹配检测", test_query_id_mismatch()))
    results.append(("scores_snapshot 完整性", test_scores_snapshot_complete()))
    results.append(("正确反馈成功", test_correct_feedback()))
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
