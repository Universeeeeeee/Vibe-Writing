[中文](#中文) | [English](#english)

---

# 中文

# Vibe Writing - 学术论文智能检索与分拣系统

一个基于 MCP (Model Context Protocol) 的学术论文自动检索、筛选与分拣系统。支持同时从 **arXiv、PubMed、Semantic Scholar** 三大学术数据库检索论文，适用于任何需要跨库文献检索的研究领域。

## 功能特点

- **三库联合检索**：同时调用 arXiv、PubMed、Semantic Scholar API，一次检索覆盖三大主流学术数据库
- **智能筛选**：基于可配置的门控策略（Gate Filter），自动过滤无关论文
- **多维标签**：自动为论文打上多维度标签，辅助分类与筛选
- **相关性评分**：自动计算论文与研究主题的相关性分数，支持排序
- **Paper Triage**：Web 前端界面，支持候选论文的浏览、筛选与反馈
- **API 服务**：基于 FastAPI 的后端 API，支持检索、存储与管理
- **MCP 集成**：作为 MCP 工具运行，可与 AI 助手无缝集成

> 项目内置了步态分析（Gait Analysis）领域的检索策略作为示例，你可以根据自己的研究方向自定义关键词和过滤规则。

## 自定义检索策略

`research_tools.py` 中预置了步态分析领域的关键词配置，包括：

| 变量名 | 用途 | 示例 |
|--------|------|------|
| `DOMAIN_KEYWORDS` | 领域词，决定论文是否属于目标领域 | `gait`, `walking`, `stride` |
| `STRONG_SYSTEM_KEYWORDS` | 系统开发相关词，用于加分 | `system`, `platform`, `framework` |
| `REPRODUCIBILITY_KEYWORDS` | 开源/可复现词，用于加分 | `github`, `open-source`, `dataset` |
| `TAG_*` 系列 | 多维标签关键词 | `TAG_ACQUISITION`, `TAG_PIPELINE` 等 |
| `EXCLUDE_KEYWORDS` | 排除词，过滤无关论文 | `rat`, `mouse`, `robot` |
| `build_query_*()` 函数 | 各数据库的查询语句构造 | 可替换为你的研究领域查询 |

**使用方法**：将上述变量中的关键词替换为你的研究领域相关词汇即可。无需修改其他文件。

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

---

# English

# Vibe Writing - Academic Paper Search & Triage System

An automated academic paper search, filtering, and triage system built on MCP (Model Context Protocol). It searches **arXiv, PubMed, and Semantic Scholar** simultaneously, suitable for any research field that requires cross-database literature retrieval.

## Features

- **Tri-Database Search**: Calls arXiv, PubMed, and Semantic Scholar APIs simultaneously, covering three major academic databases in one search
- **Smart Filtering**: Configurable gate filter strategy to automatically exclude irrelevant papers
- **Multi-Dimensional Tags**: Automatically tags papers across multiple dimensions for classification and filtering
- **Relevance Scoring**: Automatically computes relevance scores for sorting and prioritization
- **Paper Triage**: Web-based frontend for browsing, screening, and providing feedback on candidate papers
- **API Service**: FastAPI-powered backend API for search, storage, and management
- **MCP Integration**: Runs as an MCP tool, seamlessly integrating with AI assistants

> The project includes a built-in search strategy for the Gait Analysis domain as an example. You can customize the keywords and filtering rules for your own research field.

## Customizing Search Strategy

`research_tools.py` contains pre-configured keywords for the Gait Analysis domain, including:

| Variable | Purpose | Examples |
|----------|---------|----------|
| `DOMAIN_KEYWORDS` | Domain terms that determine if a paper belongs to the target field | `gait`, `walking`, `stride` |
| `STRONG_SYSTEM_KEYWORDS` | System development terms for relevance scoring | `system`, `platform`, `framework` |
| `REPRODUCIBILITY_KEYWORDS` | Open-source/reproducibility terms for scoring | `github`, `open-source`, `dataset` |
| `TAG_*` series | Multi-dimensional tagging keywords | `TAG_ACQUISITION`, `TAG_PIPELINE`, etc. |
| `EXCLUDE_KEYWORDS` | Exclusion terms to filter out irrelevant papers | `rat`, `mouse`, `robot` |
| `build_query_*()` functions | Query builders for each database | Replace with your research domain queries |

**How to use**: Simply replace the keywords in the variables above with terms relevant to your research field. No other files need to be modified.

## Project Structure

```
├── research_tools.py          # MCP Tool: arXiv/PubMed/Semantic Scholar search engine
├── requirements.txt           # Python dependencies
├── search_outouts/
│   ├── api.py                 # FastAPI backend API
│   ├── retriever.py           # Search dispatcher
│   ├── storage.py             # Data persistence (JSON)
│   └── frontend/
│       ├── index.html         # Paper Triage frontend page
│       ├── app.js             # Frontend logic
│       └── style.css          # Frontend styles
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run as MCP Tool

```bash
python research_tools.py
```

### 3. Start Paper Triage System

```bash
cd search_outouts
uvicorn api:app --reload --port 8000
```

Then visit `http://localhost:8000` in your browser.

## Tech Stack

- **Backend**: Python, FastAPI, MCP
- **Search**: arxiv API, PubMed/Entrez, Semantic Scholar API (httpx)
- **Frontend**: HTML/CSS/JavaScript
- **Data Storage**: JSON files

## License

MIT
