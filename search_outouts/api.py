"""
api.py - FastAPI 后端
Paper Triage System 的 REST API
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import concurrent.futures

from storage import (
    load_candidates, update_candidate_status, get_candidate_by_id,
    load_library, add_to_library, LibraryItem,
    load_feedback, add_feedback, FeedbackEvent,
    CandidateStatus, FeedbackLabel
)
from retriever import generate_candidates, refresh_candidates

# FastAPI 应用
app = FastAPI(
    title="Paper Triage API",
    description="文献筛选系统 API - 支持候选管理、反馈收集与参考文献库",
    version="1.0.0"
)

# CORS 配置（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务（前端）
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ============ Pydantic 模型 ============

class FeedbackRequest(BaseModel):
    paper_id: str
    query_id: Optional[str] = ""
    label: str  # "accept" or "reject"
    reason_tags: Optional[List[str]] = []
    free_text: Optional[str] = None


class RefreshRequest(BaseModel):
    max_results: Optional[int] = 5
    sources: Optional[List[str]] = ["arxiv", "pubmed", "semanticscholar"]


# 请求频率限制存储
refresh_requests = defaultdict(list)


class CandidatesResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int


class FeedbackResponse(BaseModel):
    success: bool
    event_id: str
    message: str


# ============ 根路由 ============

@app.get("/")
async def root():
    """根路由 - 返回前端页面或 API 信息"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Paper Triage API",
        "docs": "/docs",
        "endpoints": ["/api/candidates", "/api/library", "/api/feedback"]
    }


@app.get("/style.css")
async def get_style():
    """返回 CSS 文件"""
    css_path = os.path.join(FRONTEND_DIR, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")


@app.get("/app.js")
async def get_js():
    """返回 JS 文件"""
    js_path = os.path.join(FRONTEND_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS file not found")


@app.get("/favicon.ico")
async def get_favicon():
    """返回 favicon（如果存在）"""
    favicon_path = os.path.join(FRONTEND_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")


# ============ Candidates API ============

@app.get("/api/candidates", response_model=CandidatesResponse)
async def get_candidates(
    status: Optional[str] = Query(None, description="过滤状态: pending/accepted/rejected"),
    query_id: Optional[str] = Query(None, description="按查询ID过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取候选论文列表
    
    - **status**: 可选，过滤状态 (pending/accepted/rejected)
    - **query_id**: 可选，按查询ID过滤
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20
    """
    candidates = load_candidates(status=status, query_id=query_id)
    
    # 【宽松版检索策略】按 system_score 降序排序
    # 参考 2.4修改.md 第6节
    def sort_key(c):
        # 优先级1: system_score（系统开发分数，核心排序依据）
        system_score = c.get("system_score") or 0
        
        # 优先级2: app_heavy=true 的论文排后面
        app_heavy = 1 if c.get("app_heavy") else 0
        
        # 优先级3: retrieval_score 作为辅助
        retrieval_score = c.get("retrieval_score") or 0
        
        # 优先级4: accept_prob 作为学习信号（后期学习后起作用）
        accept_prob = c.get("accept_prob") or 0
        
        # 稳定 tie-break：rank 越小越靠前
        rank = c.get("rank") or 9999
        paper_id = c.get("paper_id", "")
        
        # 返回元组：app_heavy (升序，false排前), -system_score (降序), -retrieval_score (降序), rank (升序)
        return (app_heavy, -system_score, -retrieval_score, -accept_prob, rank, paper_id)
    
    candidates.sort(key=sort_key)
    
    total = len(candidates)
    start = (page - 1) * page_size
    end = start + page_size
    items = candidates[start:end]
    
    return CandidatesResponse(items=items, total=total, page=page, page_size=page_size)


@app.get("/api/candidates/{paper_id}")
async def get_candidate(paper_id: str):
    """获取单个候选详情"""
    candidate = get_candidate_by_id(paper_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Paper not found")
    return candidate


@app.post("/api/candidates/refresh")
async def refresh_candidates_endpoint(request: RefreshRequest):
    """
    刷新候选池（执行新一轮检索）
    添加用户级频率限制：每分钟最多2次

    - **max_results**: 每个源的最大结果数
    - **sources**: 检索源列表 ["arxiv", "pubmed", "semanticscholar"]
    """
    # 获取客户端IP（简化版，实际应使用 request.client.host）
    client_ip = "default"  # 实际应使用 request.client.host

    # 检查频率限制
    now = datetime.now()
    recent_requests = [
        req_time for req_time in refresh_requests[client_ip]
        if now - req_time < timedelta(minutes=1)
    ]

    if len(recent_requests) >= 2:  # 每分钟最多2次
        wait_seconds = 60 - (now - recent_requests[0]).seconds
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请等待 {wait_seconds} 秒后再试"
        )

    # 记录本次请求
    refresh_requests[client_ip].append(now)
    # 清理1小时前的记录
    refresh_requests[client_ip] = [
        req_time for req_time in refresh_requests[client_ip]
        if now - req_time < timedelta(hours=1)
    ]

    try:
        # 使用线程池执行同步检索函数，设置 120 秒超时
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await asyncio.wait_for(
                loop.run_in_executor(pool, lambda: generate_candidates(
                    max_results=request.max_results,
                    sources=request.sources
                )),
                timeout=120.0
            )

        return {
            "success": True,
            "query_id": result["query_id"],
            "added": result["added"],
            "total_retrieved": result["total_retrieved"],
            "by_source": result["by_source"]
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="检索超时，请稍后重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


# ============ Feedback API ============

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    提交审核反馈
    
    - **paper_id**: 论文ID
    - **label**: "accept" 或 "reject"
    - **reason_tags**: 可选，拒绝理由标签
    - **free_text**: 可选，自由文本备注
    """
    # 验证 label
    if request.label not in [FeedbackLabel.ACCEPT.value, FeedbackLabel.REJECT.value]:
        raise HTTPException(status_code=400, detail="Invalid label. Use 'accept' or 'reject'")
    
    # 获取候选信息
    candidate = get_candidate_by_id(request.paper_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 【修复1】query_id 一致性：强制使用 candidate.query_id，禁止"串台"
    canonical_query_id = candidate.get("query_id", "")
    if request.query_id and request.query_id != canonical_query_id:
        raise HTTPException(
            status_code=400, 
            detail=f"query_id mismatch: request={request.query_id}, candidate={canonical_query_id}"
        )
    
    # 【修复2】scores_snapshot 完整性：确保关键字段存在
    retrieval_score = candidate.get("retrieval_score")
    rank = candidate.get("rank")
    if retrieval_score is None or rank is None:
        raise HTTPException(
            status_code=400,
            detail="Candidate missing required fields (retrieval_score or rank). Cannot record feedback."
        )
    
    # 创建反馈事件
    event = FeedbackEvent(
        event_id="",  # 自动生成
        paper_id=request.paper_id,
        query_id=canonical_query_id,  # 强制使用 candidate 的 query_id
        label=request.label,
        reason_tags=request.reason_tags or [],
        free_text=request.free_text,
        scores_snapshot={
            "retrieval_score": retrieval_score,
            "rerank_score": candidate.get("rerank_score"),  # 允许 null
            "rank": rank
        }
    )
    
    # 保存反馈
    event_id = add_feedback(event)
    
    # 更新候选状态
    if request.label == FeedbackLabel.ACCEPT.value:
        update_candidate_status(request.paper_id, CandidateStatus.ACCEPTED.value)
        
        # 添加到参考文献库
        library_item = LibraryItem(
            paper_id=candidate["paper_id"],
            title=candidate["title"],
            authors=candidate["authors"],
            year=candidate["year"],
            abstract=candidate.get("abstract", ""),
            venue=candidate.get("venue"),
            doi=candidate.get("doi"),
            url_pdf=candidate.get("url_pdf"),
            url_landing=candidate.get("url_landing"),
            keywords=candidate.get("keywords", []),
            query_id=candidate.get("query_id", ""),
            retrieval_source=candidate.get("retrieval_source", ""),
            gate_level=candidate.get("gate_level", ""),
            added_by="human"
        )
        add_to_library(library_item)
        message = "Paper accepted and added to library"
    else:
        update_candidate_status(request.paper_id, CandidateStatus.REJECTED.value)
        message = "Paper rejected"
    
    return FeedbackResponse(success=True, event_id=event_id, message=message)


@app.get("/api/feedback")
async def get_feedback_history(
    since: Optional[str] = Query(None, description="ISO8601 时间戳，获取该时间后的反馈")
):
    """获取反馈历史"""
    feedback = load_feedback(since=since)
    return {"items": feedback, "total": len(feedback)}


# ============ Library API ============

@app.get("/api/library")
async def get_library(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取参考文献库"""
    library = load_library()
    
    total = len(library)
    start = (page - 1) * page_size
    end = start + page_size
    items = library[start:end]
    
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ============ Learning API ============

@app.post("/api/learn/run")
async def run_learning(
    since: Optional[str] = Query(None, description="只使用该时间后的反馈"),
    mode: str = Query("classifier", description="classifier 或 rerank_pairwise")
):
    """
    触发模型学习
    
    MVP 阶段返回 dummy 结果，后续接入真实 learner
    """
    feedback = load_feedback(since=since)
    
    if len(feedback) < 5:
        return {
            "success": False,
            "message": f"需要至少 5 条反馈数据进行训练，当前只有 {len(feedback)} 条"
        }
    
    # TODO: 接入 learner.py
    return {
        "success": True,
        "job_id": "learn_dummy_001",
        "status": "completed",
        "message": f"使用 {len(feedback)} 条反馈数据完成训练（MVP dummy）",
        "model_version": "v0.1-dummy"
    }


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
