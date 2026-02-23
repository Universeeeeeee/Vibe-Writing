/**
 * Paper Triage - 前端应用逻辑
 */

// API 基础路径
const API_BASE = 'http://localhost:8000/api';

// 应用状态
const state = {
    candidates: [],
    selectedIndex: -1,
    selectedPaper: null,
    currentStatus: '',
    currentPage: 1,
    pageSize: 20,
    totalItems: 0,
    stats: { pending: 0, accepted: 0, rejected: 0 }
};

// 刷新状态（防重复点击）
let isRefreshing = false;

// DOM 元素缓存
const elements = {
    candidatesList: document.getElementById('candidatesList'),
    detailPanel: document.getElementById('detailPanel'),
    refreshBtn: document.getElementById('refreshBtn'),
    prevPage: document.getElementById('prevPage'),
    nextPage: document.getElementById('nextPage'),
    pageInfo: document.getElementById('pageInfo'),
    pendingCount: document.getElementById('pendingCount'),
    acceptedCount: document.getElementById('acceptedCount'),
    rejectedCount: document.getElementById('rejectedCount'),
    rejectModal: document.getElementById('rejectModal'),
    cancelReject: document.getElementById('cancelReject'),
    confirmReject: document.getElementById('confirmReject'),
    rejectFreeText: document.getElementById('rejectFreeText')
};

// ============ API 调用 ============

async function fetchCandidates(status = '', page = 1) {
    try {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: state.pageSize.toString()
        });
        if (status) params.append('status', status);

        const response = await fetch(`${API_BASE}/candidates?${params}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('获取候选列表失败:', error);
        return { items: [], total: 0 };
    }
}

async function submitFeedback(paperId, label, reasonTags = [], freeText = '') {
    try {
        const response = await fetch(`${API_BASE}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper_id: paperId,
                label: label,
                reason_tags: reasonTags,
                free_text: freeText || null
            })
        });
        return await response.json();
    } catch (error) {
        console.error('提交反馈失败:', error);
        return { success: false, message: error.message };
    }
}

async function refreshCandidatesFromServer() {
    // 防止重复点击
    if (isRefreshing) {
        alert('检索正在进行中，请稍候...');
        return;
    }

    try {
        isRefreshing = true;
        elements.refreshBtn.disabled = true;
        elements.refreshBtn.innerHTML = '<span class="icon">⏳</span> 检索中...';

        // 添加60秒超时
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('请求超时 (60秒)')), 60000)
        );

        const fetchPromise = fetch(`${API_BASE}/candidates/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_results: 5 })
        });

        const response = await Promise.race([fetchPromise, timeoutPromise]);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            alert(`检索完成！新增 ${result.added} 篇候选论文`);
            await loadCandidates();
        } else {
            alert(`检索失败: ${result.message || '未知错误'}`);
        }
    } catch (error) {
        console.error('刷新失败:', error);
        alert('刷新失败: ' + error.message);
    } finally {
        isRefreshing = false;
        elements.refreshBtn.disabled = false;
        elements.refreshBtn.innerHTML = '<span class="icon">🔄</span> 刷新候选';
    }
}

// ============ 渲染函数 ============

function renderCandidatesList() {
    if (state.candidates.length === 0) {
        elements.candidatesList.innerHTML = `
            <div class="empty-state">
                <p>暂无候选论文</p>
                <p class="hint">点击"刷新候选"获取新论文</p>
            </div>
        `;
        return;
    }

    elements.candidatesList.innerHTML = state.candidates.map((paper, index) => `
        <div class="candidate-card ${index === state.selectedIndex ? 'selected' : ''} status-${paper.status || 'pending'}"
             data-index="${index}" onclick="selectPaper(${index})">
            <div class="candidate-title">${escapeHtml(paper.title)}</div>
            <div class="candidate-meta">
                <span>📅 ${paper.year || 'N/A'}</span>
                <span>📊 ${paper.retrieval_source || 'unknown'}</span>
                <span>🏷️ ${paper.gate_level || ''}</span>
            </div>
            ${paper.keywords_hit && paper.keywords_hit.length > 0 ? `
                <div class="candidate-keywords">
                    ${paper.keywords_hit.slice(0, 4).map(kw => `<span class="keyword-tag">${escapeHtml(kw)}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderDetailPanel(paper) {
    if (!paper) {
        elements.detailPanel.innerHTML = `
            <div class="detail-placeholder">
                <div class="placeholder-icon">📄</div>
                <p>选择左侧论文查看详情</p>
                <p class="hint">快捷键: J/K 上下选择, A 通过, R 拒绝</p>
            </div>
        `;
        return;
    }

    const isActionable = paper.status === 'pending';

    elements.detailPanel.innerHTML = `
        <div class="detail-content">
            <div class="detail-header">
                <h2 class="detail-title">${escapeHtml(paper.title)}</h2>
                <div class="detail-authors">
                    ${paper.authors ? paper.authors.join(', ') : '未知作者'}
                </div>
            </div>
            
            <div class="detail-section">
                <h3>摘要</h3>
                <p class="detail-abstract">${escapeHtml(paper.abstract || paper.summary || '无摘要')}</p>
            </div>
            
            <div class="detail-section">
                <h3>检索信息</h3>
                <div class="detail-scores">
                    <div class="score-item">
                        <div class="score-label">来源</div>
                        <div class="score-value">${paper.retrieval_source || 'N/A'}</div>
                    </div>
                    <div class="score-item">
                        <div class="score-label">门检级别</div>
                        <div class="score-value">${paper.gate_level || 'N/A'}</div>
                    </div>
                    <div class="score-item">
                        <div class="score-label">检索分数</div>
                        <div class="score-value">${(paper.retrieval_score || 0).toFixed(2)}</div>
                    </div>
                    <div class="score-item">
                        <div class="score-label">排名</div>
                        <div class="score-value">#${paper.rank || 'N/A'}</div>
                    </div>
                </div>
            </div>
            
            ${paper.pillar_evidence ? `
                <div class="detail-section">
                    <h3>综述支柱证据</h3>
                    <div class="detail-scores">
                        ${Object.entries(paper.pillar_evidence).map(([key, value]) => `
                            <div class="score-item">
                                <div class="score-label">${key.replace('Review_', '').replace('_Evidence', '')}</div>
                                <div class="score-value" style="font-size: 0.85rem; color: var(--text-secondary);">
                                    ${escapeHtml(value).substring(0, 100)}...
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div class="detail-section">
                <h3>链接</h3>
                <p>
                    ${paper.url_landing || paper.paper_id ?
            `<a href="${paper.url_landing || paper.paper_id}" target="_blank" style="color: var(--accent-blue);">
                            🔗 打开原文
                        </a>` : '无链接'}
                </p>
            </div>
            
            ${isActionable ? `
                <div class="detail-actions">
                    <button class="btn btn-success" onclick="acceptPaper()">
                        ✅ 通过 (A)
                    </button>
                    <button class="btn btn-danger" onclick="showRejectModal()">
                        ❌ 拒绝 (R)
                    </button>
                </div>
            ` : `
                <div class="detail-actions">
                    <div class="stat-badge ${paper.status}">
                        状态: ${paper.status === 'accepted' ? '已通过' : '已拒绝'}
                    </div>
                </div>
            `}
        </div>
    `;
}

function updateStats() {
    elements.pendingCount.textContent = `待审核: ${state.stats.pending}`;
    elements.acceptedCount.textContent = `已通过: ${state.stats.accepted}`;
    elements.rejectedCount.textContent = `已拒绝: ${state.stats.rejected}`;
}

function updatePagination() {
    const totalPages = Math.ceil(state.totalItems / state.pageSize) || 1;
    elements.pageInfo.textContent = `第 ${state.currentPage} / ${totalPages} 页`;
    elements.prevPage.disabled = state.currentPage <= 1;
    elements.nextPage.disabled = state.currentPage >= totalPages;
}

// ============ 交互逻辑 ============

function selectPaper(index) {
    state.selectedIndex = index;
    state.selectedPaper = state.candidates[index];
    renderCandidatesList();
    renderDetailPanel(state.selectedPaper);
}

async function acceptPaper() {
    if (!state.selectedPaper || state.selectedPaper.status !== 'pending') return;

    const result = await submitFeedback(state.selectedPaper.paper_id, 'accept');
    if (result.success) {
        state.selectedPaper.status = 'accepted';
        state.stats.pending--;
        state.stats.accepted++;
        updateStats();

        // 从列表中移除已审核的论文（如果在"待审核"或"全部"tab下）
        removePaperFromList();
    } else {
        alert('操作失败: ' + result.message);
    }
}

function showRejectModal() {
    if (!state.selectedPaper || state.selectedPaper.status !== 'pending') return;
    elements.rejectModal.classList.remove('hidden');
}

function hideRejectModal() {
    elements.rejectModal.classList.add('hidden');
    // 清空选择
    elements.rejectModal.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    elements.rejectFreeText.value = '';
}

async function confirmRejectPaper() {
    if (!state.selectedPaper) return;

    const reasonTags = Array.from(
        elements.rejectModal.querySelectorAll('input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    const freeText = elements.rejectFreeText.value.trim();

    const result = await submitFeedback(state.selectedPaper.paper_id, 'reject', reasonTags, freeText);
    if (result.success) {
        state.selectedPaper.status = 'rejected';
        state.stats.pending--;
        state.stats.rejected++;
        updateStats();
        hideRejectModal();

        // 从列表中移除已审核的论文
        removePaperFromList();
    } else {
        alert('操作失败: ' + result.message);
    }
}

function moveToNextPending() {
    // 找到下一个待审核的论文
    for (let i = state.selectedIndex + 1; i < state.candidates.length; i++) {
        if (state.candidates[i].status === 'pending') {
            selectPaper(i);
            return;
        }
    }
    // 如果后面没有，从头找
    for (let i = 0; i < state.selectedIndex; i++) {
        if (state.candidates[i].status === 'pending') {
            selectPaper(i);
            return;
        }
    }
}

function removePaperFromList() {
    // 从候选列表中移除当前已审核的论文
    const removedIndex = state.selectedIndex;
    state.candidates.splice(removedIndex, 1);
    state.totalItems--;

    if (state.candidates.length === 0) {
        // 列表空了，重置
        state.selectedIndex = -1;
        state.selectedPaper = null;
        renderCandidatesList();
        renderDetailPanel(null);
        updatePagination();
        return;
    }

    // 选择下一篇：优先同位置，超出则选最后一篇
    const nextIndex = Math.min(removedIndex, state.candidates.length - 1);
    state.selectedIndex = nextIndex;
    state.selectedPaper = state.candidates[nextIndex];
    
    updatePagination();
    renderCandidatesList();
    renderDetailPanel(state.selectedPaper);
}

// ============ 数据加载 ============

async function loadCandidates() {
    elements.candidatesList.innerHTML = '<div class="loading">加载中...</div>';

    const data = await fetchCandidates(state.currentStatus, state.currentPage);
    state.candidates = data.items || [];
    state.totalItems = data.total || 0;

    // 计算统计
    const allData = await fetchCandidates('', 1);
    const all = allData.items || [];
    state.stats.pending = all.filter(p => p.status === 'pending').length;
    state.stats.accepted = all.filter(p => p.status === 'accepted').length;
    state.stats.rejected = all.filter(p => p.status === 'rejected').length;

    // 重置选择
    state.selectedIndex = -1;
    state.selectedPaper = null;

    updateStats();
    updatePagination();
    renderCandidatesList();
    renderDetailPanel(null);
}

// ============ 事件绑定 ============

function bindEvents() {
    // 刷新按钮
    elements.refreshBtn.addEventListener('click', refreshCandidatesFromServer);

    // 分页
    elements.prevPage.addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            loadCandidates();
        }
    });

    elements.nextPage.addEventListener('click', () => {
        const totalPages = Math.ceil(state.totalItems / state.pageSize);
        if (state.currentPage < totalPages) {
            state.currentPage++;
            loadCandidates();
        }
    });

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.currentStatus = tab.dataset.status;
            state.currentPage = 1;
            loadCandidates();
        });
    });

    // 拒绝弹窗
    elements.cancelReject.addEventListener('click', hideRejectModal);
    elements.confirmReject.addEventListener('click', confirmRejectPaper);

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        // 如果在输入框中，忽略快捷键
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key.toLowerCase()) {
            case 'j': // 下一个
                if (state.selectedIndex < state.candidates.length - 1) {
                    selectPaper(state.selectedIndex + 1);
                }
                break;
            case 'k': // 上一个
                if (state.selectedIndex > 0) {
                    selectPaper(state.selectedIndex - 1);
                }
                break;
            case 'a': // 通过
                acceptPaper();
                break;
            case 'r': // 拒绝
                showRejectModal();
                break;
            case 'escape': // 关闭弹窗
                hideRejectModal();
                break;
        }
    });
}

// ============ 工具函数 ============

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ 初始化 ============

async function init() {
    bindEvents();
    await loadCandidates();

    // 自动选择第一个
    if (state.candidates.length > 0) {
        selectPaper(0);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
