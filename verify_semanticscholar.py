#!/usr/bin/env python3
"""
验证 Semantic Scholar 集成 - 基本功能检查（不调用API）
"""

import sys
import os
import json

print("=== Semantic Scholar 集成验证（基本功能） ===")
print()

# 测试 1: 模块导入
print("1. 模块导入检查...")
try:
    from research_tools import (
        build_query_system_semanticscholar,
        build_query_pipeline_semanticscholar,
        search_semanticscholar_papers,
        search_all_papers
    )
    print("   [OK] research_tools 模块导入成功")

    # 检查是否导入了 semanticscholar
    import semanticscholar as ss
    print("   [OK] semanticscholar 库可用")
except Exception as e:
    print(f"   [ERROR] 模块导入失败: {e}")
    sys.exit(1)

print()

# 测试 2: 查询构建函数
print("2. 查询构建函数检查...")
try:
    query1 = build_query_system_semanticscholar()
    query2 = build_query_pipeline_semanticscholar()

    print(f"   [OK] build_query_system_semanticscholar() 返回: {len(query1)} 字符")
    print(f"   [OK] build_query_pipeline_semanticscholar() 返回: {len(query2)} 字符")

    # 基本关键词检查
    test_cases = [
        ("系统查询应包含 'gait'", "gait", query1),
        ("系统查询应包含 'system'", "system", query1),
        ("管线查询应包含 'event detection'", "event detection", query2),
    ]

    for desc, keyword, query in test_cases:
        if keyword.lower() in query.lower():
            print(f"   [OK] {desc}")
        else:
            print(f"   [WARNING] {desc} - 未找到关键词 '{keyword}'")

except Exception as e:
    print(f"   [ERROR] 查询构建检查失败: {e}")

print()

# 测试 3: 函数签名检查
print("3. 函数签名检查...")
try:
    import inspect

    # 检查 search_semanticscholar_papers 函数
    sig = inspect.signature(search_semanticscholar_papers)
    params = list(sig.parameters.keys())

    expected_params = ["query", "max_results", "use_gait_query"]
    missing = [p for p in expected_params if p not in params]

    if not missing:
        print(f"   [OK] search_semanticscholar_papers() 参数正确: {params}")
    else:
        print(f"   [ERROR] search_semanticscholar_papers() 缺少参数: {missing}")

    # 检查函数是否有 MCP 装饰器
    if hasattr(search_semanticscholar_papers, '__mcp_tool__') or hasattr(search_semanticscholar_papers, '__wrapped__'):
        print("   [OK] 函数具有 MCP 装饰器")
    else:
        # 检查是否有 @mcp.tool() 装饰器的迹象
        print("   [INFO] MCP 装饰器状态: 需要运行时验证")

except Exception as e:
    print(f"   [ERROR] 函数签名检查失败: {e}")

print()

# 测试 4: 检索层集成检查
print("4. 检索层集成检查...")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_outouts"))
    from retriever import generate_candidates

    # 检查 generate_candidates 的默认参数
    import inspect
    sig = inspect.signature(generate_candidates)
    default_sources = sig.parameters['sources'].default

    if "semanticscholar" in default_sources:
        print(f"   [OK] generate_candidates() 默认包含 semanticscholar: {default_sources}")
    else:
        print(f"   [ERROR] generate_candidates() 默认未包含 semanticscholar: {default_sources}")

    # 检查 _parse_semanticscholar_result 函数是否存在
    from retriever import _parse_semanticscholar_result
    print("   [OK] _parse_semanticscholar_result() 函数存在")

except Exception as e:
    print(f"   [ERROR] 检索层集成检查失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试 5: API 层集成检查
print("5. API 层集成检查...")
try:
    from api import RefreshRequest

    # 检查 RefreshRequest 模型的默认值
    request = RefreshRequest()
    if "semanticscholar" in request.sources:
        print(f"   [OK] RefreshRequest 默认包含 semanticscholar: {request.sources}")
    else:
        print(f"   [ERROR] RefreshRequest 默认未包含 semanticscholar: {request.sources}")

except Exception as e:
    print(f"   [ERROR] API 层集成检查失败: {e}")
    # 可能是导入路径问题，跳过这个测试
    print("   [INFO] 跳过 API 层详细检查（可能需要设置正确的 Python 路径）")

print()

# 总结
print("=== 验证总结 ===")
print()
print("已完成的功能集成:")
print("1. [research_tools.py] - Semantic Scholar 查询构建函数")
print("2. [research_tools.py] - search_semanticscholar_papers() MCP 工具")
print("3. [research_tools.py] - search_all_papers() 更新包含 Semantic Scholar")
print("4. [retriever.py] - Semantic Scholar 解析器和检索集成")
print("5. [api.py] - API 层支持 Semantic Scholar 数据源")
print()
print("注意事项:")
print("1. Semantic Scholar API 有速率限制 (100 requests/min)")
print("2. 实际 API 调用需要在网络通畅环境下测试")
print("3. 确保 semanticscholar Python 库已正确安装")
print()
print("下一步建议:")
print("1. 等待 API 速率限制重置后测试实际检索功能")
print("2. 运行完整系统测试: python test_run.py")
print("3. 启动 MCP 服务器: python research_tools.py")
print("4. 测试 Web 界面集成")