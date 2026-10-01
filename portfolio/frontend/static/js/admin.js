/* ============================================================
   王耀威 · 个人主页后台管理逻辑
   ============================================================ */
'use strict';

const $ = (sel, root = document) => root.querySelector(sel);
const TOKEN_KEY = 'portfolio_admin_token';

function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function showToast(message) {
  const toast = $('#toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('is-on');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.remove('is-on'), 2600);
}

const state = { token: localStorage.getItem(TOKEN_KEY) || '', page: 1, pages: 1, pageSize: 8 };

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['x-admin-token'] = state.token;
  const response = await fetch(path, { ...options, headers: { ...headers, ...(options.headers || {}) } });
  let payload = null;
  try { payload = await response.json(); } catch (err) { payload = null; }
  if (response.status === 401) {
    logout(false);
    throw new Error('登录已过期，请重新登录');
  }
  if (!response.ok) {
    const detail = payload && payload.detail
      ? (typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail))
      : `请求失败（HTTP ${response.status}）`;
    throw new Error(detail);
  }
  return payload;
}

/* ---------------- 登录 / 登出 ---------------- */
function showLogin() {
  $('#loginView').hidden = false;
  $('#adminView').hidden = true;
}

function showAdmin(user) {
  $('#loginView').hidden = true;
  $('#adminView').hidden = false;
  if (user) $('#adminUser').textContent = `已登录：${user}`;
}

function logout(callApi = true) {
  const old = state.token;
  state.token = '';
  localStorage.removeItem(TOKEN_KEY);
  showLogin();
  if (callApi && old) {
    fetch('/api/admin/logout', { method: 'POST', headers: { 'x-admin-token': old } }).catch(() => {});
  }
}

function setupLogin() {
  const form = $('#loginForm');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const status = $('#loginStatus');
    const button = $('#loginSubmit');
    button.disabled = true;
    status.className = 'form-status';
    status.textContent = '登录中…';
    try {
      const data = await api('/api/admin/login', {
        method: 'POST',
        body: JSON.stringify({
          username: $('#loginUser').value.trim(),
          password: $('#loginPass').value,
        }),
      });
      state.token = data.token;
      localStorage.setItem(TOKEN_KEY, data.token);
      status.textContent = '';
      showAdmin(data.user);
      await refreshAll();
      showToast('登录成功');
    } catch (err) {
      status.className = 'form-status is-err';
      status.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  });
  $('#logoutBtn')?.addEventListener('click', () => { logout(); showToast('已退出登录'); });
}

/* ---------------- KPI ---------------- */
function renderKpis(data) {
  const items = [
    { label: '累计访问量', value: data.total_views, note: '所有页面请求数' },
    { label: '今日访问量', value: data.today_views, note: '今天 00:00 起' },
    { label: '今日独立访客', value: data.today_visitors, note: '按 IP 去重' },
    { label: '累计独立访客', value: data.total_visitors, note: '历史去重' },
    { label: '留言总数', value: data.total_messages, note: '含已隐藏' },
  ];
  $('#kpis').innerHTML = items.map((item) => `
    <div class="kpi">
      <span>${escapeHtml(item.label)}</span>
      <b>${Number(item.value) || 0}</b>
      <i>${escapeHtml(item.note)}</i>
    </div>`).join('');
}

/* ---------------- 趋势图 ---------------- */
function renderTrend(daily) {
  const box = $('#trendChart');
  if (!box) return;
  const list = daily || [];
  const max = Math.max(1, ...list.map((d) => d.views));
  const maxVisitors = Math.max(1, ...list.map((d) => d.visitors));
  const bars = list.map((item) => {
    const height = Math.max(2, Math.round((item.views / max) * 100));
    const dotBottom = Math.max(0, Math.min(100, (item.visitors / maxVisitors) * 100));
    return `
      <div class="chart__col" title="${item.day}｜访问 ${item.views}｜访客 ${item.visitors}">
        <div class="chart__bars">
          <div class="chart__bar" style="height:${height}%"></div>
          <span class="chart__dot" style="bottom:${dotBottom}%"></span>
        </div>
        <span class="chart__label">${escapeHtml(item.label)}</span>
      </div>`;
  }).join('');
  box.innerHTML = bars || '<p class="muted small">暂无访问数据</p>';
}

/* ---------------- 热门页面 / 最近访问 ---------------- */
function renderTopPages(list) {
  const box = $('#topPages');
  if (!box) return;
  if (!list || !list.length) { box.innerHTML = '<li class="muted small">暂无数据</li>'; return; }
  const max = Math.max(...list.map((p) => p.views));
  box.innerHTML = list.map((item, i) => `
    <li>
      <span class="rank__no">${i + 1}</span>
      <span class="rank__path">${escapeHtml(item.path)}</span>
      <span class="rank__bar"><i style="width:${Math.round((item.views / max) * 100)}%"></i></span>
      <span class="rank__val">${item.views}</span>
    </li>`).join('');
}

function renderRecentVisits(list) {
  const box = $('#recentVisits');
  if (!box) return;
  if (!list || !list.length) { box.innerHTML = '<li class="muted small">暂无数据</li>'; return; }
  box.innerHTML = list.map((item) => `
    <li>
      <span><em>${escapeHtml(item.path)}</em> · ${escapeHtml(item.ip)} · ${escapeHtml(item.device)}</span>
      <span>${escapeHtml(item.created_at)}</span>
    </li>`).join('');
}

/* ---------------- 留言表格 ---------------- */
function renderMessages(data) {
  const tbody = $('#msgTable');
  if (!data.items.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-row">没有匹配的留言</td></tr>';
    $('#adminPager').innerHTML = '';
    return;
  }
  tbody.innerHTML = data.items.map((item) => `
    <tr>
      <td class="table__meta">#${item.id}</td>
      <td>${escapeHtml(item.name)}</td>
      <td class="table__content">${escapeHtml(item.content)}</td>
      <td class="table__contact">${escapeHtml(item.contact) || '<span class="muted">—</span>'}</td>
      <td class="table__meta">${escapeHtml(item.ip)}<br>${escapeHtml(item.device)}</td>
      <td class="table__meta">${escapeHtml(item.created_at)}</td>
      <td><span class="badge ${item.approved ? 'badge--on' : 'badge--off'}">${item.approved ? '已公开' : '已隐藏'}</span></td>
      <td>
        <div class="row-actions">
          <button data-act="toggle" data-id="${item.id}" data-approved="${item.approved ? 0 : 1}">${item.approved ? '隐藏' : '公开'}</button>
          <button data-act="delete" data-id="${item.id}" class="danger">删除</button>
        </div>
      </td>
    </tr>`).join('');
  renderPager(data);
}

function renderPager(data) {
  const pager = $('#adminPager');
  if (data.pages <= 1) { pager.innerHTML = ''; return; }
  const buttons = [`<button data-page="${data.page - 1}" ${data.page <= 1 ? 'disabled' : ''}>‹</button>`];
  for (let i = 1; i <= data.pages; i += 1) {
    if (data.pages > 9 && Math.abs(i - data.page) > 2 && i !== 1 && i !== data.pages) {
      if (i === 2 || i === data.pages - 1) buttons.push('<button disabled>…</button>');
      continue;
    }
    buttons.push(`<button data-page="${i}" class="${i === data.page ? 'is-on' : ''}">${i}</button>`);
  }
  buttons.push(`<button data-page="${data.page + 1}" ${data.page >= data.pages ? 'disabled' : ''}>›</button>`);
  pager.innerHTML = buttons.join('');
}

async function loadMessages(page = state.page) {
  const keyword = $('#msgKeyword').value.trim();
  const approved = $('#msgFilter').value;
  const params = new URLSearchParams({ page: String(page), page_size: String(state.pageSize) });
  if (keyword) params.set('keyword', keyword);
  if (approved !== '') params.set('approved', approved);
  const data = await api(`/api/admin/messages?${params.toString()}`);
  state.page = data.page;
  state.pages = data.pages;
  renderMessages(data);
}

function setupMessageTools() {
  $('#msgSearch')?.addEventListener('click', () => loadMessages(1));
  $('#msgKeyword')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); loadMessages(1); }
  });
  $('#msgFilter')?.addEventListener('change', () => loadMessages(1));
  $('#adminPager')?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-page]');
    if (!button || button.disabled) return;
    loadMessages(Number(button.dataset.page));
  });
  $('#msgTable')?.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-act]');
    if (!button) return;
    const id = Number(button.dataset.id);
    button.disabled = true;
    try {
      if (button.dataset.act === 'toggle') {
        await api(`/api/admin/messages/${id}?approved=${button.dataset.approved}`, { method: 'PATCH' });
        showToast(button.dataset.approved === '1' ? '留言已公开' : '留言已隐藏');
      } else {
        if (!window.confirm(`确认删除留言 #${id}？此操作不可撤销。`)) { button.disabled = false; return; }
        await api(`/api/admin/messages/${id}`, { method: 'DELETE' });
        showToast('留言已删除');
      }
      await Promise.all([loadMessages(), loadOverview()]);
    } catch (err) {
      showToast(err.message);
      button.disabled = false;
    }
  });
}

/* ---------------- 刷新 ---------------- */
async function loadOverview() {
  const data = await api('/api/admin/overview');
  renderKpis(data);
  renderTrend(data.daily);
  renderTopPages(data.top_pages);
  renderRecentVisits(data.recent_visits);
}

async function refreshAll() {
  try {
    await Promise.all([loadOverview(), loadMessages(1)]);
  } catch (err) {
    showToast(err.message);
  }
}

/* ---------------- 启动 ---------------- */
document.addEventListener('DOMContentLoaded', async () => {
  setupLogin();
  setupMessageTools();
  if (!state.token) { showLogin(); return; }
  try {
    showAdmin('');
    await refreshAll();
  } catch (err) {
    showLogin();
    $('#loginStatus').className = 'form-status is-err';
    $('#loginStatus').textContent = err.message;
  }
});
