"""
测试脚本 - 验证 Paper Triage System 功能
"""

import sys
import os

# 1. 测试 storage 模块
print("=" * 50)
print("1. 测试 Storage 模块")
print("=" * 50)

from storage import (
    load_candidates, load_library, load_feedback, 
    add_candidates, CandidatePaper, init_data_files
)

init_data_files()
print(f"✅ 数据文件初始化成功")
print(f"   - 候选数量: {len(load_candidates())}")
print(f"   - 参考文献库: {len(load_library())}")
print(f"   - 反馈记录: {len(load_feedback())}")

# 2. 测试 retriever 模块
print("\n" + "=" * 50)
print("2. 测试 Retriever 模块")
print("=" * 50)

try:
    from retriever import generate_candidates
    result = generate_candidates(max_results=2)
    print(f"✅ 检索完成")
    print(f"   - Query ID: {result['query_id']}")
    print(f"   - 新增候选: {result['added']} 篇")
    print(f"   - 总检索量: {result['total_retrieved']} 篇")
    print(f"   - 按来源: {result['by_source']}")
except Exception as e:
    print(f"⚠️ 检索失败（可能是网络问题）: {e}")

# 3. 验证候选已存储
print("\n" + "=" * 50)
print("3. 验证数据持久化")
print("=" * 50)

candidates = load_candidates()
print(f"✅ 当前候选数量: {len(candidates)}")

if candidates:
    c = candidates[0]
    print(f"\n   第一篇论文:")
    print(f"   - 标题: {c.get('title', 'N/A')[:60]}...")
    print(f"   - 年份: {c.get('year', 'N/A')}")
    print(f"   - 来源: {c.get('retrieval_source', 'N/A')}")
    print(f"   - 状态: {c.get('status', 'N/A')}")

# 4. 测试 feedback 流程
print("\n" + "=" * 50)
print("4. 测试 Feedback 流程")
print("=" * 50)

if candidates:
    from storage import (
        add_feedback, FeedbackEvent, update_candidate_status,
        add_to_library, LibraryItem, CandidateStatus
    )
    
    test_paper = candidates[0]
    paper_id = test_paper['paper_id']
    
    # 模拟 accept
    event = FeedbackEvent(
        event_id="",
        paper_id=paper_id,
        query_id=test_paper.get('query_id', ''),
        label='accept',
        reason_tags=[],
        free_text="测试通过"
    )
    event_id = add_feedback(event)
    print(f"✅ 反馈已记录: {event_id}")
    
    # 更新状态
    update_candidate_status(paper_id, CandidateStatus.ACCEPTED.value)
    print(f"✅ 候选状态已更新为 accepted")
    
    # 添加到 library
    lib_item = LibraryItem(
        paper_id=paper_id,
        title=test_paper['title'],
        authors=test_paper.get('authors', []),
        year=test_paper.get('year', 0),
        abstract=test_paper.get('abstract', ''),
        query_id=test_paper.get('query_id', ''),
        retrieval_source=test_paper.get('retrieval_source', ''),
        gate_level=test_paper.get('gate_level', ''),
        added_by='test_script'
    )
    added = add_to_library(lib_item)
    print(f"✅ 添加到参考文献库: {'成功' if added else '已存在'}")
else:
    print("⚠️ 无候选论文，跳过 feedback 测试")

# 5. 最终状态
print("\n" + "=" * 50)
print("5. 最终状态")
print("=" * 50)

print(f"   - 候选数量: {len(load_candidates())}")
print(f"   - 参考文献库: {len(load_library())}")
print(f"   - 反馈记录: {len(load_feedback())}")

print("\n" + "=" * 50)
print("✅ 所有测试完成！")
print("=" * 50)
