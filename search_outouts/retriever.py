"""
retriever.py - 检索模块
包装 research_tools.py 的检索函数，生成候选池
"""

import sys
import os
import json
import uuid
from datetime import datetime
from typing import List, Optional

# 添加父目录到路径以导入 research_tools
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from research_tools import search_arxiv_papers, search_pubmed_papers, search_semanticscholar_papers
from storage import CandidatePaper, add_candidates, CandidateStatus


def generate_query_id() -> str:
    """生成唯一的查询 ID"""
    return f"q_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


def _parse_arxiv_result(paper: dict, query_id: str, query_text: str, rank: int) -> CandidatePaper:
    """解析 arXiv 检索结果（适配宽松版检索策略）"""
    # 使用 system_score 作为 retrieval_score（体现系统开发优先）
    system_score = paper.get("system_score", 0.0)
    
    return CandidatePaper(
        paper_id=paper.get("url", f"arxiv_{uuid.uuid4().hex[:8]}"),
        title=paper.get("title", ""),
        authors=paper.get("authors", []),
        year=paper.get("year", 0),
        abstract=paper.get("summary", ""),
        url_landing=paper.get("url", ""),
        keywords=paper.get("keywords_hit", []),
        query_id=query_id,
        query_text=query_text,
        retrieval_score=max(0.5 + system_score * 0.1, 0.1),  # 基于 system_score 计算
        rank=rank,
        retrieval_source="arxiv",
        gate_level=paper.get("gate_level", ""),
        keywords_hit=paper.get("keywords_hit", []),
        pillar_evidence=paper.get("pillar_evidence", {}),
        # 【新增】宽松版字段
        tags=paper.get("tags", []),
        system_score=system_score,
        app_heavy=paper.get("app_heavy", False),
        tag_evidence=paper.get("tag_evidence", {}),
        exclude_hit=paper.get("exclude_hit")
    )


def _parse_pubmed_result(paper: dict, query_id: str, query_text: str, rank: int) -> CandidatePaper:
    """解析 PubMed 检索结果（适配宽松版检索策略）"""
    pmid = paper.get("pmid", "")
    system_score = paper.get("system_score", 0.0)
    
    return CandidatePaper(
        paper_id=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else f"pubmed_{uuid.uuid4().hex[:8]}",
        title=paper.get("title", ""),
        authors=paper.get("authors", []),
        year=int(paper.get("year", 0)) if paper.get("year") else 0,
        abstract=paper.get("abstract", ""),
        url_landing=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        keywords=paper.get("keywords_hit", []),
        query_id=query_id,
        query_text=query_text,
        retrieval_score=max(0.5 + system_score * 0.1, 0.1),  # 基于 system_score 计算
        rank=rank,
        retrieval_source="pubmed",
        gate_level=paper.get("gate_level", ""),
        keywords_hit=paper.get("keywords_hit", []),
        pillar_evidence=paper.get("pillar_evidence", {}),
        # 【新增】宽松版字段
        tags=paper.get("tags", []),
        system_score=system_score,
        app_heavy=paper.get("app_heavy", False),
        tag_evidence=paper.get("tag_evidence", {}),
        exclude_hit=paper.get("exclude_hit")
    )


def _parse_semanticscholar_result(paper: dict, query_id: str, query_text: str, rank: int) -> CandidatePaper:
    """解析 Semantic Scholar 检索结果（适配宽松版检索策略）"""
    system_score = paper.get("system_score", 0.0)

    return CandidatePaper(
        paper_id=paper.get("paper_id", f"semanticscholar_{uuid.uuid4().hex[:8]}"),
        title=paper.get("title", ""),
        authors=paper.get("authors", []),
        year=paper.get("year", 0),
        abstract=paper.get("abstract", ""),
        url_landing=paper.get("url", ""),
        keywords=paper.get("keywords_hit", []),
        query_id=query_id,
        query_text=query_text,
        retrieval_score=max(0.5 + system_score * 0.1, 0.1),  # 基于 system_score 计算
        rank=rank,
        retrieval_source="semanticscholar",
        gate_level=paper.get("gate_level", ""),
        keywords_hit=paper.get("keywords_hit", []),
        pillar_evidence=paper.get("pillar_evidence", {}),
        # 【新增】宽松版字段
        tags=paper.get("tags", []),
        system_score=system_score,
        app_heavy=paper.get("app_heavy", False),
        tag_evidence=paper.get("tag_evidence", {}),
        exclude_hit=paper.get("exclude_hit")
    )


def generate_candidates(
    max_results: int = 10,
    use_gait_query: bool = True,
    custom_query: Optional[str] = None,
    sources: List[str] = ["arxiv", "pubmed", "semanticscholar"]
) -> dict:
    """
    生成候选论文池
    
    Args:
        max_results: 每个源的最大结果数
        use_gait_query: 是否使用预定义的步态分析检索式
        custom_query: 自定义查询（如果提供则覆盖 use_gait_query）
        sources: 检索源列表
    
    Returns:
        dict: {"query_id": str, "added": int, "total_retrieved": int, "by_source": dict}
    """
    query_id = generate_query_id()
    query_text = custom_query if custom_query else "gait analysis system (auto-generated)"
    
    all_candidates: List[CandidatePaper] = []
    by_source = {}
    
    rank_offset = 0
    
    # arXiv 检索
    if "arxiv" in sources:
        try:
            arxiv_json = search_arxiv_papers(
                query=custom_query or "",
                max_results=max_results,
                use_gait_query=use_gait_query and not custom_query
            )
            arxiv_results = json.loads(arxiv_json)
            
            for i, paper in enumerate(arxiv_results):
                candidate = _parse_arxiv_result(paper, query_id, query_text, rank_offset + i + 1)
                all_candidates.append(candidate)
            
            by_source["arxiv"] = len(arxiv_results)
            rank_offset += len(arxiv_results)
        except Exception as e:
            by_source["arxiv"] = f"error: {str(e)}"
    
    # PubMed 检索
    if "pubmed" in sources:
        try:
            pubmed_json = search_pubmed_papers(
                query=custom_query or "",
                max_results=max_results,
                use_gait_query=use_gait_query and not custom_query
            )
            pubmed_results = json.loads(pubmed_json)
            
            if isinstance(pubmed_results, list):
                for i, paper in enumerate(pubmed_results):
                    candidate = _parse_pubmed_result(paper, query_id, query_text, rank_offset + i + 1)
                    all_candidates.append(candidate)
                by_source["pubmed"] = len(pubmed_results)
            else:
                by_source["pubmed"] = f"error: {pubmed_results.get('error', 'unknown')}"
        except Exception as e:
            by_source["pubmed"] = f"error: {str(e)}"

    # Semantic Scholar 检索
    if "semanticscholar" in sources:
        try:
            semanticscholar_json = search_semanticscholar_papers(
                query=custom_query or "",
                max_results=max_results,
                use_gait_query=use_gait_query and not custom_query
            )
            semanticscholar_results = json.loads(semanticscholar_json)

            if isinstance(semanticscholar_results, list):
                for i, paper in enumerate(semanticscholar_results):
                    candidate = _parse_semanticscholar_result(paper, query_id, query_text, rank_offset + i + 1)
                    all_candidates.append(candidate)
                by_source["semanticscholar"] = len(semanticscholar_results)
                rank_offset += len(semanticscholar_results)
            else:
                by_source["semanticscholar"] = f"error: {semanticscholar_results.get('error', 'unknown')}"
        except Exception as e:
            by_source["semanticscholar"] = f"error: {str(e)}"

    # 添加到候选池（自动去重）
    added = add_candidates(all_candidates)
    
    return {
        "query_id": query_id,
        "added": added,
        "total_retrieved": len(all_candidates),
        "by_source": by_source
    }


def refresh_candidates(max_results: int = 5) -> dict:
    """
    刷新候选池（执行新一轮检索）
    这是一个便捷函数，使用默认参数
    """
    return generate_candidates(max_results=max_results)


if __name__ == "__main__":
    print("开始生成候选论文...")
    result = generate_candidates(max_results=3)
    print(f"\n检索结果:")
    print(f"  Query ID: {result['query_id']}")
    print(f"  新增候选: {result['added']} 篇")
    print(f"  总检索量: {result['total_retrieved']} 篇")
    print(f"  按来源: {result['by_source']}")
