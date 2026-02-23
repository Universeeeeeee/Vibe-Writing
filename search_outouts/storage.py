"""
storage.py - 数据模型与持久化
Paper Triage System 的核心数据层
"""

import json
import hashlib
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# 数据文件路径
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
LIBRARY_FILE = os.path.join(DATA_DIR, "library.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")


class FeedbackLabel(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"


class CandidateStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"  # 重复项


@dataclass
class CandidatePaper:
    """候选论文数据结构"""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str = ""
    venue: Optional[str] = None
    doi: Optional[str] = None
    url_pdf: Optional[str] = None
    url_landing: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    # 检索与排序信息
    query_id: str = ""
    query_text: str = ""
    retrieval_score: float = 0.0
    rerank_score: Optional[float] = None
    accept_prob: Optional[float] = None
    rank: int = 0
    retrieval_source: str = ""
    retrieved_at: str = ""
    
    # 状态与去重
    status: str = CandidateStatus.PENDING.value
    fingerprint: str = ""
    is_duplicate_of: Optional[str] = None
    
    # 门检结果（来自 research_tools）
    gate_level: str = ""
    keywords_hit: List[str] = field(default_factory=list)
    pillar_evidence: Dict[str, str] = field(default_factory=dict)
    
    # 【新增】宽松版检索策略字段（2.4修改.md）
    tags: List[str] = field(default_factory=list)           # 命中的Tag: Acquisition/Pipeline/Software/Data
    system_score: float = 0.0                               # 系统开发分数
    app_heavy: bool = False                                 # 是否纯应用论文
    tag_evidence: Dict[str, str] = field(default_factory=dict)  # 每个Tag的证据句
    exclude_hit: Optional[str] = None                       # 命中的排除词（降权用）
    
    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self._compute_fingerprint()
        if not self.retrieved_at:
            self.retrieved_at = datetime.utcnow().isoformat() + "Z"
    
    def _compute_fingerprint(self) -> str:
        """计算论文指纹（用于去重）"""
        text = f"{self.title.lower().strip()}|{self.year}|{','.join(sorted(a.lower() for a in self.authors[:3]))}"
        return hashlib.md5(text.encode()).hexdigest()[:16]


@dataclass
class LibraryItem:
    """参考文献库条目"""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str = ""
    venue: Optional[str] = None
    doi: Optional[str] = None
    url_pdf: Optional[str] = None
    url_landing: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    # 来源追踪
    query_id: str = ""
    retrieval_source: str = ""
    gate_level: str = ""
    
    # 入库信息
    added_at: str = ""
    added_by: str = "human"
    
    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.utcnow().isoformat() + "Z"


@dataclass
class FeedbackEvent:
    """人工反馈事件"""
    event_id: str
    paper_id: str
    query_id: str
    label: str  # accept / reject
    reason_tags: List[str] = field(default_factory=list)
    free_text: Optional[str] = None
    
    # 模型快照
    model_snapshot: Dict[str, Any] = field(default_factory=dict)
    scores_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    created_at: str = ""
    created_by: str = "human"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if not self.event_id:
            self.event_id = hashlib.md5(f"{self.paper_id}{self.created_at}".encode()).hexdigest()[:12]


# ============ 持久化函数 ============

def _load_json(filepath: str, default: Any = None) -> Any:
    """加载 JSON 文件"""
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default if default is not None else []


def _save_json(filepath: str, data: Any) -> None:
    """保存 JSON 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============ Candidates 操作 ============

def load_candidates(status: Optional[str] = None, query_id: Optional[str] = None, include_duplicates: bool = False) -> List[Dict]:
    """加载候选论文列表
    
    Args:
        status: 过滤状态
        query_id: 过滤查询ID  
        include_duplicates: 是否包含重复项（默认不包含）
    """
    candidates = _load_json(CANDIDATES_FILE, [])
    # 默认排除 duplicate 状态
    if not include_duplicates:
        candidates = [c for c in candidates if c.get("status") != "duplicate"]
    if status:
        candidates = [c for c in candidates if c.get("status") == status]
    if query_id:
        candidates = [c for c in candidates if c.get("query_id") == query_id]
    return candidates


def save_candidates(candidates: List[Dict]) -> None:
    """保存候选论文列表"""
    _save_json(CANDIDATES_FILE, candidates)


def add_candidates(new_candidates: List[CandidatePaper]) -> int:
    """添加候选论文（自动去重，但保留重复信息以便追踪）"""
    existing = load_candidates()
    # 建立 fingerprint -> paper_id 映射
    fp_to_paper_id = {c.get("fingerprint"): c.get("paper_id") for c in existing}
    existing_fps = set(fp_to_paper_id.keys())
    
    added = 0
    for c in new_candidates:
        c_dict = asdict(c)
        fp = c_dict["fingerprint"]
        
        if fp in existing_fps:
            # 【修复4】重复项不静默跳过，而是标记为 duplicate
            c_dict["status"] = "duplicate"
            c_dict["is_duplicate_of"] = fp_to_paper_id.get(fp)
            existing.append(c_dict)
            # 不计入 added 统计（因为是重复的）
        else:
            existing.append(c_dict)
            existing_fps.add(fp)
            fp_to_paper_id[fp] = c_dict["paper_id"]
            added += 1
    
    save_candidates(existing)
    return added


def update_candidate_status(paper_id: str, status: str) -> bool:
    """更新候选状态"""
    candidates = load_candidates()
    for c in candidates:
        if c.get("paper_id") == paper_id:
            c["status"] = status
            save_candidates(candidates)
            return True
    return False


def get_candidate_by_id(paper_id: str) -> Optional[Dict]:
    """根据 ID 获取候选"""
    candidates = load_candidates()
    for c in candidates:
        if c.get("paper_id") == paper_id:
            return c
    return None


# ============ Library 操作 ============

def load_library() -> List[Dict]:
    """加载参考文献库"""
    return _load_json(LIBRARY_FILE, [])


def save_library(library: List[Dict]) -> None:
    """保存参考文献库"""
    _save_json(LIBRARY_FILE, library)


def add_to_library(item: LibraryItem) -> bool:
    """添加到参考文献库（幂等）"""
    library = load_library()
    
    # 检查是否已存在
    for existing in library:
        if existing.get("paper_id") == item.paper_id:
            return False  # 已存在，不重复添加
    
    library.append(asdict(item))
    save_library(library)
    return True


# ============ Feedback 操作 ============

def load_feedback(since: Optional[str] = None) -> List[Dict]:
    """加载反馈事件"""
    feedback = _load_json(FEEDBACK_FILE, [])
    if since:
        feedback = [f for f in feedback if f.get("created_at", "") >= since]
    return feedback


def save_feedback(feedback: List[Dict]) -> None:
    """保存反馈事件"""
    _save_json(FEEDBACK_FILE, feedback)


def add_feedback(event: FeedbackEvent) -> str:
    """添加反馈事件（只追加不覆盖）"""
    feedback = load_feedback()
    event_dict = asdict(event)
    feedback.append(event_dict)
    save_feedback(feedback)
    return event.event_id


# ============ 初始化 ============

def init_data_files() -> None:
    """初始化数据文件（如果不存在）"""
    for filepath, default in [
        (CANDIDATES_FILE, []),
        (LIBRARY_FILE, []),
        (FEEDBACK_FILE, [])
    ]:
        if not os.path.exists(filepath):
            _save_json(filepath, default)


if __name__ == "__main__":
    init_data_files()
    print(f"数据文件已初始化:")
    print(f"  - {CANDIDATES_FILE}")
    print(f"  - {LIBRARY_FILE}")
    print(f"  - {FEEDBACK_FILE}")
