# Vibe Writing - 学术论文智能检索与分拣系统

一个基于 MCP (Model Context Protocol) 的学术论文自动检索、筛选与分拣系统，专注于步态分析领域的文献综述辅助。

## 功能特点

- **多源检索**：同时从 arXiv、PubMed、Semantic Scholar 三大学术数据库检索论文
- **智能筛选**：基于宽松版门控策略（Gate Filter），自动过滤无关论文
- **多维标签**：自动为论文打上 Acquisition / Pipeline / Software / Data 四维标签
- **系统评分**：根据系统开发相关性计算 system_score，支持排序
- **Paper Triage**：Web 前端界面，支持候选论文的浏览、筛选与反馈
- **API 服务**：基于 FastAPI 的后端 API，支持检索、存储与管理

## 项目结构

```
├── research_tools.py          # MCP 工具：arXiv/PubMed/Semantic Scholar 检索引擎
├── requirements.txt           # Python 依赖
├── search_outouts/
│   ├── api.py                 # FastAPI 后端 API
│   ├── retriever.py           # 检索调度器
│   ├── storage.py             # 数据持久化（JSON）
│   └── frontend/
│       ├── index.html         # Paper Triage 前端页面
│       ├── app.js             # 前端逻辑
│       └── style.css          # 前端样式
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 作为 MCP 工具运行

```bash
python research_tools.py
```

### 3. 启动 Paper Triage 系统

```bash
cd search_outouts
uvicorn api:app --reload --port 8000
```

然后在浏览器中访问 `http://localhost:8000`

## 技术栈

- **后端**：Python, FastAPI, MCP
- **检索**：arxiv API, PubMed/Entrez, Semantic Scholar API (httpx)
- **前端**：HTML/CSS/JavaScript
- **数据存储**：JSON 文件

## License

MIT
