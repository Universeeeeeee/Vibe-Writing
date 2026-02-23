from mcp.server.fastmcp import FastMCP
import arxiv
import httpx  # 替代 semanticscholar 库
from Bio import Entrez, Medline
import json
import re
import time
from threading import Lock
from functools import wraps
from typing import List, Dict, Tuple

# 初始化 MCP 服务
mcp = FastMCP("Academic-Search-Engine")

# 设置 PubMed 邮箱 (NCBI 要求)
Entrez.email = "lzr20011221@gmail.com"

# ============ 宽松版检索策略关键词配置 ============
# 参考 2.4修改.md：面向"步态分析系统开发/软件工程"

# 1. 领域词（宽松版：命中任意即可）
DOMAIN_KEYWORDS = [
    "gait", "walking", "locomotion", "stride", "step", 
    "spatiotemporal", "step detection", "gait event",
    "gait analysis"
]

# 2. 强系统词（用于 system_score 加分）
STRONG_SYSTEM_KEYWORDS = [
    "system", "platform", "framework", "software", "toolkit", "pipeline"
]

# 3. 开源/复现词（用于 system_score 加分）
REPRODUCIBILITY_KEYWORDS = [
    "github", "open-source", "open source", "code available", 
    "dataset", "public", "benchmark", "reproducibility"
]

# 4. 四大 Tag 关键词组（用于打标签，不决定 pass/fail）

# Tag-A: 采集与硬件接口 (Acquisition)
TAG_ACQUISITION = [
    "sensor", "imu", "wearable", "pressure", "optical", "camera", 
    "depth", "synchronized", "calibration", "accelerometer", "gyroscope"
]

# Tag-B: 算法管线 (Pipeline & Algorithms)
TAG_PIPELINE = [
    "preprocessing", "filtering", "segmentation", "event detection",
    "stride length", "cadence", "spatiotemporal", "feature extraction",
    "classification", "cnn", "transformer", "model deployment",
    "deep learning", "machine learning", "neural network", "algorithm"
]

# Tag-C: 软件系统与交互 (Software & HCI)
TAG_SOFTWARE = [
    "gui", "visualization", "dashboard", "interface", "app", 
    "usability", "interactive", "feedback", "display", "user experience"
]

# Tag-D: 数据与交付 (Data & Reporting)
TAG_DATA = [
    "database", "data management", "cloud", "report", "ehr",
    "logging", "export", "standardization", "electronic health record"
]

# 5. 应用强信号词（用于 app_heavy 检测和降权）
APP_HEAVY_KEYWORDS = [
    "patient", "clinical trial", "cohort", "intervention", 
    "rehabilitation", "postoperative", "diagnosis", "outcome", "symptom",
    "parkinson", "stroke", "cerebral palsy", "osteoarthritis",
    "therapy", "treatment", "recovery"
]

# 6. 排除词（宽松版：只排"确定不是"的）
EXCLUDE_KEYWORDS = [
    "rat", "mouse", "animal", "quadruped",  # 动物实验
    "gene", "cell", "molecular",             # 分子/细胞
    "robot", "robotic", "prosthesis design"  # 纯机器人（注意：用作测量平台的可保留）
]

# ============ Semantic Scholar httpx 客户端 ============
# 使用 httpx 直接调用 API，完全控制重试逻辑

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,abstract,authors,year,venue,citationCount,url,externalIds,publicationTypes"

# 全局速率限制
_ss_last_call_time = 0
_ss_min_interval = 1.0  # 最小请求间隔（秒）


def _semantic_scholar_search_httpx(query: str, limit: int = 15, offset: int = 0) -> dict:
    """
    使用 httpx 直接调用 Semantic Scholar API
    包含重试逻辑和速率限制
    """
    global _ss_last_call_time
    
    # 速率限制：确保请求间隔
    now = time.time()
    elapsed = now - _ss_last_call_time
    if elapsed < _ss_min_interval:
        time.sleep(_ss_min_interval - elapsed)
    
    params = {
        "query": query,
        "fields": SEMANTIC_SCHOLAR_FIELDS,
        "offset": offset,
        "limit": limit
    }
    
    max_retries = 3
    for retry in range(max_retries):
        try:
            # 重试时使用指数退避
            if retry > 0:
                wait_time = 10 * (2 ** (retry - 1))  # 10, 20, 40秒
                print(f"Semantic Scholar 重试 {retry}/{max_retries}，等待 {wait_time} 秒...")
                time.sleep(wait_time)
            
            _ss_last_call_time = time.time()
            
            with httpx.Client(timeout=30.0) as client:
                response = client.get(SEMANTIC_SCHOLAR_API_URL, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    print(f"Semantic Scholar 429 (请求过快)，将重试...")
                    if retry == max_retries - 1:
                        return {"error": "429 Too Many Requests", "data": []}
                    continue
                elif response.status_code >= 500:
                    print(f"Semantic Scholar {response.status_code} 服务器错误，将重试...")
                    if retry == max_retries - 1:
                        return {"error": f"Server Error {response.status_code}", "data": []}
                    continue
                else:
                    return {"error": f"HTTP {response.status_code}", "data": []}
                    
        except httpx.TimeoutException:
            print(f"Semantic Scholar 请求超时，将重试...")
            if retry == max_retries - 1:
                return {"error": "Timeout", "data": []}
            continue
        except Exception as e:
            print(f"Semantic Scholar 请求异常: {e}")
            return {"error": str(e), "data": []}
    
    return {"error": "Max retries exceeded", "data": []}

# ============ Query 构造（双Query策略） ============

def build_query_system_arxiv() -> str:
    """
    Query-1：系统开发主召回（偏软件）
    """
    query = '''(gait OR walking OR stride OR step OR locomotion)
    AND (system OR platform OR framework OR pipeline OR software OR toolkit 
         OR "open source" OR github OR implementation OR real-time 
         OR wearable OR smartphone OR visualization OR dashboard OR GUI 
         OR database OR report)
    AND submittedDate:[20180101 TO 20261231]'''
    return ' '.join(query.split())

def build_query_pipeline_arxiv() -> str:
    """
    Query-2：算法管线补召回（避免只讲算法的核心论文被漏）
    """
    query = '''(gait OR walking OR stride OR step)
    AND ("event detection" OR segmentation OR preprocessing OR spatiotemporal 
         OR "stride length" OR cadence OR kinematics OR "signal processing" 
         OR "feature extraction" OR validation)
    AND submittedDate:[20180101 TO 20261231]'''
    return ' '.join(query.split())

def build_query_system_pubmed() -> str:
    """
    Query-1 PubMed版：系统开发主召回
    """
    query = '''(gait[Title/Abstract] OR walking[Title/Abstract]) 
    AND (system[Title/Abstract] OR platform[Title/Abstract] OR software[Title/Abstract] 
         OR visualization[Title/Abstract] OR database[Title/Abstract] 
         OR "real-time"[Title/Abstract] OR wearable[Title/Abstract])
    AND 2018:2026[dp]'''
    return ' '.join(query.split())

def build_query_pipeline_pubmed() -> str:
    """
    Query-2 PubMed版：算法管线补召回
    """
    query = '''(gait[Title/Abstract] OR walking[Title/Abstract])
    AND (algorithm[Title/Abstract] OR validation[Title/Abstract]
         OR accuracy[Title/Abstract] OR detection[Title/Abstract])
    AND 2018:2026[dp]'''
    return ' '.join(query.split())

def build_query_system_semanticscholar() -> str:
    """
    Query-1 Semantic Scholar版：系统开发主召回
    """
    query = '''(gait OR walking OR stride OR step OR locomotion)
    AND (system OR platform OR framework OR pipeline OR software OR toolkit
         OR "open source" OR github OR implementation OR real-time
         OR wearable OR smartphone OR visualization OR dashboard OR GUI
         OR database OR report)'''
    return ' '.join(query.split())

def build_query_pipeline_semanticscholar() -> str:
    """
    Query-2 Semantic Scholar版：算法管线补召回
    """
    query = '''(gait OR walking OR stride OR step)
    AND ("event detection" OR segmentation OR preprocessing OR spatiotemporal
         OR "stride length" OR cadence OR kinematics OR "signal processing"
         OR "feature extraction" OR validation)'''
    return ' '.join(query.split())

# ============ Gate 过滤（宽松版） ============

def gate_filter_relaxed(title: str, abstract: str) -> dict:
    """
    宽松版门检逻辑：宁可放进来，别在门口误杀
    返回 dict: {"pass": bool, "level": str, "missing": [], "hits": [], "exclude_hit": str|None}
    """
    title_lower = title.lower()
    abstract_lower = abstract.lower()
    text = title_lower + " " + abstract_lower
    
    # Gate-1：领域词（宽松：命中任意即可）
    domain_hit = any(kw.lower() in text for kw in DOMAIN_KEYWORDS)
    if not domain_hit:
        return {"pass": False, "level": "reject", "missing": ["未命中领域词"], "hits": [], "exclude_hit": None}
    
    # Gate-2：排除词（但如果同时命中强系统词则降权而非reject）
    exclude_hit = None
    strong_system_hit = any(kw.lower() in text for kw in STRONG_SYSTEM_KEYWORDS)
    
    for exclude_word in EXCLUDE_KEYWORDS:
        pattern = r'\b' + re.escape(exclude_word.lower()) + r'\b'
        if re.search(pattern, text):
            if strong_system_hit:
                # 同时命中系统词，降权但不reject
                exclude_hit = exclude_word
                break
            else:
                # 无系统词保护，直接reject
                return {"pass": False, "level": "reject", "missing": [f"排除词: {exclude_word}"], "hits": [], "exclude_hit": exclude_word}
    
    # 收集所有命中的关键词
    all_hits = []
    for kw in STRONG_SYSTEM_KEYWORDS + REPRODUCIBILITY_KEYWORDS:
        if kw.lower() in text:
            all_hits.append(kw)
    
    # 判断级别
    if strong_system_hit:
        level = "system"
    else:
        level = "base"
    
    return {"pass": True, "level": level, "missing": [], "hits": all_hits, "exclude_hit": exclude_hit}

# ============ 打标签（用于展示与排序） ============

def compute_tags(title: str, abstract: str) -> List[str]:
    """
    计算命中的 Tag（4个维度）
    返回: ["Acquisition", "Pipeline", "Software", "Data"] 中命中的标签
    """
    text = (title + " " + abstract).lower()
    tags = []
    
    if any(kw.lower() in text for kw in TAG_ACQUISITION):
        tags.append("Acquisition")
    if any(kw.lower() in text for kw in TAG_PIPELINE):
        tags.append("Pipeline")
    if any(kw.lower() in text for kw in TAG_SOFTWARE):
        tags.append("Software")
    if any(kw.lower() in text for kw in TAG_DATA):
        tags.append("Data")
    
    return tags

# ============ System Score 计算 ============

def compute_system_score(title: str, abstract: str) -> float:
    """
    计算系统开发分数（用于排序）
    参考 2.4修改.md 第6节
    """
    text = (title + " " + abstract).lower()
    score = 0.0
    
    # +2：命中强系统词
    for kw in STRONG_SYSTEM_KEYWORDS:
        if kw.lower() in text:
            score += 2.0
            break  # 只加一次
    
    # +2：命中开源/复现词
    for kw in REPRODUCIBILITY_KEYWORDS:
        if kw.lower() in text:
            score += 2.0
            break
    
    # +1：命中软件交互
    if any(kw.lower() in text for kw in TAG_SOFTWARE):
        score += 1.0
    
    # +1：命中数据交付
    if any(kw.lower() in text for kw in TAG_DATA):
        score += 1.0
    
    # +1：命中实时/部署
    realtime_keywords = ["real-time", "online", "latency", "embedded", "edge"]
    if any(kw in text for kw in realtime_keywords):
        score += 1.0
    
    # -1~-3：应用强信号（按命中数扣分）
    app_hit_count = sum(1 for kw in APP_HEAVY_KEYWORDS if kw.lower() in text)
    score -= min(app_hit_count, 3)  # 最多扣3分
    
    return score

# ============ App Heavy 检测 ============

def detect_app_heavy(title: str, abstract: str) -> bool:
    """
    检测是否为"纯应用"论文
    条件：应用信号强 + 系统信号弱
    """
    text = (title + " " + abstract).lower()
    
    # 应用信号强度
    app_hit_count = sum(1 for kw in APP_HEAVY_KEYWORDS if kw.lower() in text)
    
    # 系统信号强度
    system_hit = any(kw.lower() in text for kw in STRONG_SYSTEM_KEYWORDS)
    repro_hit = any(kw.lower() in text for kw in REPRODUCIBILITY_KEYWORDS)
    
    # 判定：应用信号≥3 且 无系统/复现信号
    if app_hit_count >= 3 and not (system_hit or repro_hit):
        return True
    return False

# ============ 证据提取（保留原有功能） ============

def extract_evidence_sentences(text: str, keywords: list) -> list:
    """从原文中提取包含关键词的证据句"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    evidence = []
    for kw in keywords:
        for sent in sentences:
            if kw.lower() in sent.lower() and sent not in evidence:
                evidence.append(sent.strip())
                break
    return evidence

def extract_tag_evidence(title: str, abstract: str) -> Dict[str, str]:
    """
    为每个 Tag 抽取一句证据
    """
    text = title + " " + abstract
    tag_keywords = {
        "Acquisition": TAG_ACQUISITION,
        "Pipeline": TAG_PIPELINE,
        "Software": TAG_SOFTWARE,
        "Data": TAG_DATA
    }
    
    evidence = {}
    for tag, kws in tag_keywords.items():
        sents = extract_evidence_sentences(text, kws)
        if sents:
            evidence[tag] = sents[0][:200] + "..." if len(sents[0]) > 200 else sents[0]
        else:
            evidence[tag] = ""
    return evidence

# ============ 检索函数 ============

@mcp.tool()
def search_arxiv_papers(query: str = "", max_results: int = 10, use_gait_query: bool = True) -> str:
    """
    Search arXiv for gait analysis / system development papers.
    使用双Query策略：系统开发主召回 + 算法管线补召回
    """
    client = arxiv.Client()
    all_results = []
    seen_ids = set()
    
    # 双 Query 并行检索
    queries = []
    if use_gait_query:
        queries = [build_query_system_arxiv(), build_query_pipeline_arxiv()]
    else:
        queries = [query]
    
    for q in queries:
        search = arxiv.Search(
            query=q,
            max_results=max_results * 3,
            sort_by=arxiv.SortCriterion.Relevance
        )
        for r in client.results(search):
            if r.entry_id in seen_ids:
                continue
            seen_ids.add(r.entry_id)
            
            gate_result = gate_filter_relaxed(r.title, r.summary)
            if gate_result["pass"]:
                tags = compute_tags(r.title, r.summary)
                system_score = compute_system_score(r.title, r.summary)
                app_heavy = detect_app_heavy(r.title, r.summary)
                tag_evidence = extract_tag_evidence(r.title, r.summary)
                
                all_results.append({
                    "title": r.title,
                    "authors": [a.name for a in r.authors],
                    "year": r.published.year,
                    "summary": r.summary,
                    "url": r.entry_id,
                    "gate_level": gate_result["level"],
                    "keywords_hit": gate_result["hits"],
                    "tags": tags,
                    "system_score": system_score,
                    "app_heavy": app_heavy,
                    "tag_evidence": tag_evidence,
                    "exclude_hit": gate_result["exclude_hit"]
                })
            
            if len(all_results) >= max_results:
                break
        if len(all_results) >= max_results:
            break
    
    # 按 system_score 降序排序
    all_results.sort(key=lambda x: -x["system_score"])
    return json.dumps(all_results[:max_results], indent=2, ensure_ascii=False)

@mcp.tool()
def search_pubmed_papers(query: str = "", max_results: int = 10, use_gait_query: bool = True) -> str:
    """
    Search PubMed for gait analysis / system development papers.
    使用双Query策略
    """
    try:
        all_results = []
        seen_pmids = set()
        
        # 双 Query 并行检索
        queries = []
        if use_gait_query:
            queries = [build_query_system_pubmed(), build_query_pipeline_pubmed()]
        else:
            queries = [query]
        
        for q in queries:
            handle = Entrez.esearch(db="pubmed", term=q, retmax=max_results * 3)
            record = Entrez.read(handle)
            id_list = record["IdList"]
            if not id_list:
                continue
            
            handle = Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="medline", retmode="text")
            records = list(Medline.parse(handle))
            
            for rec in records:
                pmid = rec.get("PMID", "")
                if pmid in seen_pmids:
                    continue
                seen_pmids.add(pmid)
                
                title = rec.get("TI", "")
                abstract = rec.get("AB", "")
                
                gate_result = gate_filter_relaxed(title, abstract)
                if gate_result["pass"]:
                    tags = compute_tags(title, abstract)
                    system_score = compute_system_score(title, abstract)
                    app_heavy = detect_app_heavy(title, abstract)
                    tag_evidence = extract_tag_evidence(title, abstract)
                    
                    all_results.append({
                        "title": title,
                        "authors": rec.get("AU", []),
                        "year": rec.get("DP", "")[:4],
                        "abstract": abstract,
                        "pmid": pmid,
                        "gate_level": gate_result["level"],
                        "keywords_hit": gate_result["hits"],
                        "tags": tags,
                        "system_score": system_score,
                        "app_heavy": app_heavy,
                        "tag_evidence": tag_evidence,
                        "exclude_hit": gate_result["exclude_hit"]
                    })
                
                if len(all_results) >= max_results:
                    break
            if len(all_results) >= max_results:
                break
        
        # 按 system_score 降序排序
        all_results.sort(key=lambda x: -x["system_score"])
        return json.dumps(all_results[:max_results], indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_semanticscholar_papers(query: str = "", max_results: int = 10, use_gait_query: bool = True) -> str:
    """
    Search Semantic Scholar for gait analysis / system development papers.
    使用双Query策略：系统开发主召回 + 算法管线补召回
    使用 httpx 直接调用 API，完全控制重试逻辑
    """
    print(f"=== 开始 Semantic Scholar 检索 (httpx): query='{query}', max_results={max_results}, use_gait_query={use_gait_query} ===")
    try:
        all_results = []
        seen_ids = set()

        # 双 Query 检索
        queries = []
        if use_gait_query:
            queries = [build_query_system_semanticscholar(), build_query_pipeline_semanticscholar()]
        else:
            queries = [query]

        for i, q in enumerate(queries):
            # 查询间添加延迟（避免突发请求）
            if i > 0:
                time.sleep(2.0)

            # 使用 httpx 调用 API
            response = _semantic_scholar_search_httpx(q, limit=max_results * 2)
            
            if "error" in response and response.get("error"):
                print(f"Semantic Scholar 查询 {i+1} 失败: {response['error']}")
                continue
            
            papers = response.get("data", [])
            print(f"Semantic Scholar 查询 {i+1} 返回 {len(papers)} 篇论文")

            # 处理论文
            for paper in papers:
                paper_id = paper.get('paperId', '')
                if not paper_id or paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)

                # 提取必要字段
                title = paper.get('title', '') or ''
                abstract = paper.get('abstract', '') or ''
                authors_raw = paper.get('authors', []) or []
                authors = [author.get('name', '') for author in authors_raw if author]
                year = paper.get('year', 0) or 0
                if isinstance(year, str):
                    try:
                        year = int(year[:4]) if year else 0
                    except ValueError:
                        year = 0
                venue = paper.get('venue', '') or ''
                citation_count = paper.get('citationCount', 0) or 0

                # 应用现有处理流水线
                gate_result = gate_filter_relaxed(title, abstract)
                if gate_result["pass"]:
                    tags = compute_tags(title, abstract)
                    system_score = compute_system_score(title, abstract)
                    app_heavy = detect_app_heavy(title, abstract)
                    tag_evidence = extract_tag_evidence(title, abstract)

                    # 构建 URL
                    url = paper.get('url', '') or ''
                    external_ids = paper.get('externalIds', {}) or {}
                    if not url and external_ids.get('DOI'):
                        url = f"https://doi.org/{external_ids['DOI']}"

                    all_results.append({
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "abstract": abstract,
                        "venue": venue,
                        "citation_count": citation_count,
                        "url": url,
                        "paper_id": paper_id,
                        "gate_level": gate_result["level"],
                        "keywords_hit": gate_result["hits"],
                        "tags": tags,
                        "system_score": system_score,
                        "app_heavy": app_heavy,
                        "tag_evidence": tag_evidence,
                        "exclude_hit": gate_result["exclude_hit"]
                    })

                if len(all_results) >= max_results:
                    break

            if len(all_results) >= max_results:
                break

        # 按 system_score 降序排序
        all_results.sort(key=lambda x: -x["system_score"])
        print(f"=== Semantic Scholar 检索完成，共 {len(all_results)} 篇有效论文 ===")
        return json.dumps(all_results[:max_results], indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"=== Semantic Scholar 检索异常: {e} ===")
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_all_papers(query: str = "", max_results: int = 5, use_gait_query: bool = True) -> str:
    """
    综合检索 arXiv、PubMed 和 Semantic Scholar，返回合并结果
    """
    arxiv_json = search_arxiv_papers(query, max_results, use_gait_query)
    pubmed_json = search_pubmed_papers(query, max_results, use_gait_query)
    semanticscholar_json = search_semanticscholar_papers(query, max_results, use_gait_query)

    try:
        arxiv_results = json.loads(arxiv_json)
    except Exception:
        arxiv_results = []

    try:
        pubmed_results = json.loads(pubmed_json)
    except Exception:
        pubmed_results = []

    try:
        semanticscholar_results = json.loads(semanticscholar_json)
    except Exception:
        semanticscholar_results = []

    return json.dumps({
        "arxiv": arxiv_results,
        "pubmed": pubmed_results,
        "semanticscholar": semanticscholar_results
    }, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()