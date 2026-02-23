#!/usr/bin/env python3
"""
Test script for research_tools.py
"""
import sys
import json

# Import the module
import research_tools

print("Testing research_tools.py...")
print("=" * 50)

# Test arXiv search
print("Testing arXiv search (max_results=3)...")
try:
    result_json = research_tools.search_arxiv_papers(max_results=3, use_gait_query=True)
    result = json.loads(result_json)
    print(f"Found {len(result)} papers:")
    for i, paper in enumerate(result):
        print(f"\n{i+1}. {paper['title']}")
        print(f"   Year: {paper['year']}")
        print(f"   System Score: {paper['system_score']}")
        print(f"   Tags: {', '.join(paper['tags'])}")
        print(f"   App Heavy: {paper['app_heavy']}")
        print(f"   URL: {paper['url']}")
except Exception as e:
    print(f"Error during arXiv search: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)

# Test PubMed search
print("Testing PubMed search (max_results=2)...")
try:
    result_json = research_tools.search_pubmed_papers(max_results=2, use_gait_query=True)
    result = json.loads(result_json)
    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Found {len(result)} papers:")
        for i, paper in enumerate(result):
            print(f"\n{i+1}. {paper['title']}")
            print(f"   Year: {paper['year']}")
            print(f"   System Score: {paper['system_score']}")
            print(f"   Tags: {', '.join(paper['tags'])}")
            print(f"   App Heavy: {paper['app_heavy']}")
            print(f"   PMID: {paper['pmid']}")
except Exception as e:
    print(f"Error during PubMed search: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Test completed.")