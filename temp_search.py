"""
测试加强版领域检查
"""
from research_tools import search_arxiv_papers, search_pubmed_papers
import json
import importlib
import research_tools
importlib.reload(research_tools)
from research_tools import search_arxiv_papers, search_pubmed_papers

lines = []
def log(msg):
    print(msg)
    lines.append(str(msg))

# ============ arXiv 检索 ============
log("=" * 60)
log("arXiv 检索（10篇）")
log("=" * 60)

try:
    arxiv_result = search_arxiv_papers(max_results=10, use_gait_query=True)
    arxiv_data = json.loads(arxiv_result)
    
    if arxiv_data:
        p = arxiv_data[0]
        log(f"\n标题: {p['title']}")
        log(f"年份: {p['year']}")
        log(f"URL: {p['url']}")
        log(f"门检级别: {p['gate_level']}")
        log(f"命中关键词: {p['keywords_hit']}")
    else:
        log("未找到")
except Exception as e:
    log(f"出错: {e}")

# ============ PubMed 检索 ============
log("\n" + "=" * 60)
log("PubMed 检索（10篇）")
log("=" * 60)

try:
    pubmed_result = search_pubmed_papers(max_results=10, use_gait_query=True)
    pubmed_data = json.loads(pubmed_result)
    
    if isinstance(pubmed_data, list) and pubmed_data:
        p = pubmed_data[0]
        log(f"\n标题: {p['title']}")
        log(f"年份: {p['year']}")
        log(f"PMID: {p['pmid']}")
        log(f"URL: https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/")
        log(f"门检级别: {p['gate_level']}")
        log(f"命中关键词: {p['keywords_hit']}")
    elif isinstance(pubmed_data, dict) and "error" in pubmed_data:
        log(f"出错: {pubmed_data['error']}")
    else:
        log("未找到符合条件的文章")
except Exception as e:
    log(f"出错: {e}")

log("\n" + "=" * 60)
log("检索完成!")
log("=" * 60)

with open("test_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
