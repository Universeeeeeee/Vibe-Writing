#!/usr/bin/env python3
"""
测试 Semantic Scholar 集成功能
"""

import sys
import os
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Semantic Scholar 集成测试 ===")
print()

# 测试 1: 导入模块
print("1. 测试模块导入...")
try:
    from research_tools import (
        build_query_system_semanticscholar,
        build_query_pipeline_semanticscholar,
        search_semanticscholar_papers,
        search_all_papers
    )
    print("   [OK] 模块导入成功")
except Exception as e:
    print(f"   [ERROR] 模块导入失败: {e}")
    sys.exit(1)

print()

# 测试 2: 查询构建函数
print("2. 测试查询构建函数...")
try:
    query1 = build_query_system_semanticscholar()
    query2 = build_query_pipeline_semanticscholar()

    print(f"   [OK] 系统查询构建成功 (长度: {len(query1)} 字符)")
    print(f"   [OK] 管线查询构建成功 (长度: {len(query2)} 字符)")

    # 检查是否包含关键词
    required_keywords = ["gait", "system", "event detection"]
    for kw in required_keywords:
        if kw in query1.lower() or kw in query2.lower():
            print(f"   [OK] 查询包含关键词: {kw}")
        else:
            print(f"   [WARNING]  查询可能缺少关键词: {kw}")
except Exception as e:
    print(f"   [ERROR] 查询构建测试失败: {e}")

print()

# 测试 3: Semantic Scholar 检索（小规模测试）
print("3. 测试 Semantic Scholar 检索（max_results=2）...")
try:
    result_json = search_semanticscholar_papers(max_results=2, use_gait_query=True)
    result = json.loads(result_json)

    if isinstance(result, dict) and "error" in result:
        print(f"   [ERROR] API 调用错误: {result['error']}")
    elif isinstance(result, list):
        print(f"   [OK] 成功检索到 {len(result)} 篇论文")

        for i, paper in enumerate(result):
            print(f"\n   论文 {i+1}:")
            print(f"    标题: {paper.get('title', '无标题')[:80]}...")
            print(f"    年份: {paper.get('year', '未知')}")
            print(f"    系统评分: {paper.get('system_score', 0.0)}")
            print(f"    标签: {', '.join(paper.get('tags', []))}")
            print(f"    引用数: {paper.get('citation_count', '未知')}")
            print(f"    来源: {paper.get('venue', '未知')}")
    else:
        print(f"   [WARNING]  返回结果格式异常: {type(result)}")
except Exception as e:
    print(f"   [ERROR] Semantic Scholar 检索测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试 4: 综合检索测试
print("4. 测试综合检索（包含 Semantic Scholar）...")
try:
    result_json = search_all_papers(max_results=1, use_gait_query=True)
    result = json.loads(result_json)

    if isinstance(result, dict):
        print("   [OK] 综合检索成功")
        for source in ["arxiv", "pubmed", "semanticscholar"]:
            count = len(result.get(source, []))
            print(f"     {source}: {count} 篇论文")
    else:
        print(f"   [WARNING]  综合检索返回格式异常: {type(result)}")
except Exception as e:
    print(f"   [ERROR] 综合检索测试失败: {e}")

print()

# 测试 5: 检索层集成测试
print("5. 测试检索层集成...")
try:
    # 添加 search_outouts 目录到路径
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_outouts"))
    from retriever import generate_candidates

    result = generate_candidates(
        max_results=1,
        sources=["semanticscholar"],  # 只测试 Semantic Scholar
        use_gait_query=True
    )

    print(f"   [OK] 检索层集成成功")
    print(f"     查询ID: {result['query_id']}")
    print(f"     新增候选: {result['added']}")
    print(f"     总检索量: {result['total_retrieved']}")
    print(f"     按来源: {result['by_source']}")
except Exception as e:
    print(f"   [ERROR] 检索层集成测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=== 测试完成 ===")
print()

# 总结
print("总结:")
print("-" * 40)
print("1. 确保所有核心功能模块正常工作")
print("2. 验证 Semantic Scholar API 调用成功")
print("3. 确认数据处理流水线正常工作")
print("4. 检查与现有系统的集成")
print()
print("下一步:")
print("1. 运行完整的系统测试: python test_run.py")
print("2. 启动 MCP 服务器: python research_tools.py")
print("3. 启动 API 服务器: cd search_outouts && python api.py")
print("4. 访问前端界面: http://localhost:8000")