/* ============================================================
   王耀威 · 个人主页前端逻辑
   数据来源：本站 FastAPI 后端 (/api/*)
   ============================================================ */
'use strict';

/* ---------------- 工具函数 ---------------- */
const $ = (sel, root = document) => root.querySelector(sel);

function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function text(node, value) {
  if (node) node.textContent = value == null ? '' : String(value);
}

function showToast(message) {
  const toast = $('#toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('is-on');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.remove('is-on'), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  let payload = null;
  try {
    payload = await response.json();
  } catch (err) {
    payload = null;
  }
  if (!response.ok) {
    const detail = payload && payload.detail
      ? (typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail))
      : `请求失败（HTTP ${response.status}）`;
    throw new Error(detail);
  }
  return payload;
}

/* ---------------- 个人信息 ---------------- */
function renderProfile(profile) {
  const { name, nameEn, headline, school, major, degree, graduation, location,
          targetRole, phone, email, tagline, highlights, social } = profile;

  text($('#heroName'), name);
  text($('#heroSchool'), `${school} · ${major.replace('专业', '')}`);
  text($('#heroHeadline'), headline);
  text($('#heroTagline'), tagline);
  text($('#cardName'), name);
  text($('#cardTarget'), targetRole);
  text($('#cardDegree'), `${degree}在读`);
  text($('#cardMajor'), major);
  text($('#cardGrad'), graduation);
  text($('#cardCity'), location);
  document.title = `${name} · ${targetRole}`;

  const meta = $('#heroMeta');
  if (meta) {
    meta.innerHTML = [
      school, `${major} · ${degree}`, `毕业 ${graduation}`, location,
    ].map((item) => `<span>${escapeHtml(item)}</span>`).join('');
  }

  const contacts = $('#cardContacts');
  if (contacts) {
    const items = [
      { label: '电话', href: `tel:${phone.replace(/-/g, '')}`, value: phone },
      { label: '邮箱', href: `mailto:${email}`, value: email },
      { label: 'GitHub', href: (social.find((s) => s.icon === 'github') || {}).url || '#', value: 'GitHub' },
    ];
    contacts.innerHTML = items
      .map((item) => `<a href="${escapeHtml(item.href)}" title="${escapeHtml(item.value)}">${escapeHtml(item.label)}</a>`)
      .join('');
  }

  const contactList = $('#contactList');
  if (contactList) {
    contactList.innerHTML = [
      ['电话', `<a href="tel:${escapeHtml(phone.replace(/-/g, ''))}">${escapeHtml(phone)}</a>`],
      ['邮箱', `<a href="mailto:${escapeHtml(email)}">${escapeHtml(email)}</a>`],
      ['地区', escapeHtml(location)],
      ['求职', escapeHtml(targetRole)],
    ].map(([label, value]) => `<li><span>${label}</span><div>${value}</div></li>`).join('');
  }

  const stats = $('#heroStats');
  if (stats && highlights) {
    stats.innerHTML = highlights
      .map((item) => `<div class="stat"><b>${escapeHtml(item.value)}</b><span>${escapeHtml(item.label)}</span></div>`)
      .join('');
  }

  text($('#footerRole'), targetRole.split(' ')[0]);
}

/* ---------------- 教育经历 ---------------- */
function renderEducation(list, courses) {
  const box = $('#educationTimeline');
  if (!box) return;
  box.innerHTML = list.map((item) => `
    <article class="tl-item reveal">
      <div class="card">
        <div class="tl-item__head">
          <div>
            <h3 class="tl-item__title">${escapeHtml(item.school)}</h3>
            <p class="tl-item__org">${escapeHtml(item.major)} · ${escapeHtml(item.degree)}</p>
          </div>
          <span class="tl-item__period">${escapeHtml(item.period)}</span>
        </div>
        <div class="course-grid">
          ${(courses || item.courses || []).map((c) => `<span class="chip">${escapeHtml(c)}</span>`).join('')}
        </div>
      </div>
    </article>`).join('');
}

/* ---------------- 实习 / 工作经历 ---------------- */
function renderExperience(list) {
  const box = $('#experienceTimeline');
  if (!box) return;
  box.innerHTML = list.map((item) => `
    <article class="tl-item reveal">
      <div class="card">
        <div class="tl-item__head">
          <div>
            <h3 class="tl-item__title">${escapeHtml(item.title)}</h3>
            <p class="tl-item__org">${escapeHtml(item.org)}</p>
          </div>
          <span class="tl-item__period">${escapeHtml(item.period)}</span>
        </div>
        <ul class="tl-item__body">
          ${item.points.map((p) => `<li>${escapeHtml(p)}</li>`).join('')}
        </ul>
        <div class="tag-row">
          ${item.stack.map((s) => `<span class="tag">${escapeHtml(s)}</span>`).join('')}
        </div>
      </div>
    </article>`).join('');
}

/* ---------------- 项目经历（含筛选） ---------------- */
function projectCard(project, index) {
  return `
    <article class="project reveal" data-accent="${escapeHtml(project.accent || 'cyan')}">
      <div class="project__top">
        <h3 class="project__title">${escapeHtml(project.title)}</h3>
        <span class="project__badge">0${index + 1}</span>
      </div>
      <p class="project__summary">${escapeHtml(project.summary)}</p>
      <ul class="project__points">
        ${project.points.map((p) => `<li>${escapeHtml(p)}</li>`).join('')}
      </ul>
      ${project.metrics && project.metrics.length ? `
        <div class="project__metrics">
          ${project.metrics.map((m) => `<div><b>${escapeHtml(m.value)}</b><span>${escapeHtml(m.label)}</span></div>`).join('')}
        </div>` : ''}
      <div class="tag-row">
        ${project.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
      </div>
    </article>`;
}

function renderProjects(projects) {
  const grid = $('#projectGrid');
  const filters = $('#projectFilters');
  if (!grid) return;

  const draw = (list) => {
    grid.innerHTML = list.length
      ? list.map(projectCard).join('')
      : '<div class="empty">没有匹配的项目</div>';
    observeReveal(grid);
  };
  draw(projects);

  if (!filters) return;
  const tags = [];
  projects.forEach((p) => p.tags.forEach((t) => { if (!tags.includes(t)) tags.push(t); }));
  const buttons = [{ label: '全部', value: '*' }]
    .concat(tags.slice(0, 8).map((t) => ({ label: t, value: t })));

  filters.innerHTML = buttons
    .map((b, i) => `<button class="filter${i === 0 ? ' is-on' : ''}" data-tag="${escapeHtml(b.value)}">${escapeHtml(b.label)}</button>`)
    .join('');

  filters.addEventListener('click', (event) => {
    const button = event.target.closest('.filter');
    if (!button) return;
    filters.querySelectorAll('.filter').forEach((el) => el.classList.remove('is-on'));
    button.classList.add('is-on');
    const tag = button.dataset.tag;
    draw(tag === '*'
      ? projects
      : projects.filter((p) => p.tags.some((t) => t.toLowerCase() === tag.toLowerCase())));
  });
}

/* ---------------- 技能 ---------------- */
const SKILL_ICONS = {
  code: '{ }', brain: '🧠', eye: '👁', spark: '✦', tool: '🔧',
};

function renderSkills(skills, learning) {
  const grid = $('#skillGrid');
  if (grid) {
    grid.innerHTML = skills.map((skill) => `
      <article class="skill reveal">
        <div class="skill__head">
          <span class="skill__icon">${escapeHtml(SKILL_ICONS[skill.icon] || '◆')}</span>
          <h4>${escapeHtml(skill.category)}</h4>
        </div>
        <div class="skill__bar"><i data-level="${Number(skill.level) || 0}"></i></div>
        <div class="skill__items">
          ${skill.items.map((i) => `<span>${escapeHtml(i)}</span>`).join('')}
        </div>
      </article>`).join('');
  }

  const chips = $('#learningChips');
  if (chips && learning) {
    chips.innerHTML = learning
      .map((item) => `<span class="chip"><b>${escapeHtml(item.name)}</b><i>${escapeHtml(item.desc)}</i></span>`)
      .join('');
  }

  // 技能条进入视口后再增长，动画更自然
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.querySelectorAll('.skill__bar i').forEach((bar) => {
        bar.style.width = `${Math.max(0, Math.min(100, Number(bar.dataset.level)))}%`;
      });
      io.unobserve(entry.target);
    });
  }, { threshold: 0.25 });
  if (grid) io.observe(grid);
}

/* ---------------- 校园经历 ---------------- */
function renderCampus(list, about) {
  const grid = $('#campusGrid');
  if (grid) {
    grid.innerHTML = list.map((item) => `
      <article class="card campus__item reveal">
        <span class="campus__dot">★</span>
        <div>
          <h4>${escapeHtml(item.org)}</h4>
          <em>${escapeHtml(item.role)}${item.period ? ' · ' + escapeHtml(item.period) : ''}</em>
          <p>${escapeHtml(item.desc)}</p>
        </div>
      </article>`).join('');
  }
  text($('#aboutText'), about);
}

/* ---------------- 访问统计 ---------------- */
async function trackVisit() {
  try {
    const data = await api('/api/visit', {
      method: 'POST',
      body: JSON.stringify({ path: location.pathname || '/' }),
    });
    text($('#navViews'), data.total_views);
    const footer = $('#footerStats');
    if (footer) {
      footer.innerHTML = `
        <span>累计访问 <b>${data.total_views}</b></span>
        <span>今日访问 <b>${data.today_views}</b></span>
        <span>今日访客 <b>${data.today_visitors}</b></span>`;
    }
  } catch (err) {
    text($('#navViews'), '--');
  }
}

/* ---------------- 留言板 ---------------- */
const board = { page: 1, pageSize: 6, pages: 1 };

function messageHtml(item) {
  return `
    <article class="msg">
      <div class="msg__head">
        <span class="msg__name">${escapeHtml(item.name)}</span>
        <span class="msg__time">${escapeHtml(item.created_at)}</span>
      </div>
      <p class="msg__body">${escapeHtml(item.content)}</p>
      <p class="msg__foot">${escapeHtml(item.device)}</p>
    </article>`;
}

async function loadMessages(page = 1) {
  const list = $('#messageList');
  const pager = $('#messagePager');
  if (!list) return;
  list.innerHTML = '<div class="empty">加载中…</div>';
  try {
    const data = await api(`/api/messages?page=${page}&page_size=${board.pageSize}`);
    board.page = data.page;
    board.pages = data.pages;
    text($('#msgTotal'), data.total);
    list.innerHTML = data.items.length
      ? data.items.map(messageHtml).join('')
      : '<div class="empty">还没有留言，来做第一个吧 ✨</div>';
    renderPager(data);
  } catch (err) {
    list.innerHTML = `<div class="empty">留言加载失败：${escapeHtml(err.message)}</div>`;
    if (pager) pager.innerHTML = '';
  }
}

function renderPager(data) {
  const pager = $('#messagePager');
  if (!pager) return;
  if (data.pages <= 1) { pager.innerHTML = ''; return; }
  const buttons = [
    `<button data-page="${data.page - 1}" ${data.page <= 1 ? 'disabled' : ''}>‹</button>`,
  ];
  for (let i = 1; i <= data.pages; i += 1) {
    if (data.pages > 7 && Math.abs(i - data.page) > 2 && i !== 1 && i !== data.pages) {
      if (i === 2 || i === data.pages - 1) buttons.push('<button disabled>…</button>');
      continue;
    }
    buttons.push(`<button data-page="${i}" class="${i === data.page ? 'is-on' : ''}">${i}</button>`);
  }
  buttons.push(`<button data-page="${data.page + 1}" ${data.page >= data.pages ? 'disabled' : ''}>›</button>`);
  pager.innerHTML = buttons.join('');
}

function setupMessageForm() {
  const form = $('#messageForm');
  const input = $('#msgContent');
  const counter = $('#msgCounter');
  if (!form) return;

  input.addEventListener('input', () => {
    text(counter, `${input.value.length}/500`);
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const status = $('#msgStatus');
    const submit = $('#msgSubmit');
    const content = input.value.trim();
    if (!content) {
      status.className = 'form-status is-err';
      text(status, '留言内容不能为空');
      return;
    }
    submit.disabled = true;
    status.className = 'form-status';
    text(status, '提交中…');
    try {
      await api('/api/messages', {
        method: 'POST',
        body: JSON.stringify({
          name: $('#msgName').value.trim() || '匿名访客',
          contact: $('#msgContact').value.trim(),
          content,
        }),
      });
      form.reset();
      text(counter, '0/500');
      status.className = 'form-status is-ok';
      text(status, '留言已写入数据库 ✓');
      showToast('留言提交成功，感谢你的反馈！');
      await loadMessages(1);
    } catch (err) {
      status.className = 'form-status is-err';
      text(status, err.message);
    } finally {
      submit.disabled = false;
    }
  });

  $('#msgRefresh')?.addEventListener('click', () => loadMessages(board.page));
  $('#messagePager')?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-page]');
    if (!button || button.disabled) return;
    loadMessages(Number(button.dataset.page));
  });
}

/* ---------------- 滚动与导航交互 ---------------- */
function observeReveal(root = document) {
  const items = root.querySelectorAll('.reveal:not(.is-in)');
  if (!('IntersectionObserver' in window)) {
    items.forEach((el) => el.classList.add('is-in'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (!entry.isIntersecting) return;
      setTimeout(() => entry.target.classList.add('is-in'), i * 60);
      io.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  items.forEach((el) => io.observe(el));
}

function setupScrollUi() {
  const nav = $('#nav');
  const progress = $('#navProgress');
  const toTop = $('#toTop');
  const links = Array.from(document.querySelectorAll('.nav__links a'));
  const sections = links
    .map((a) => document.querySelector(a.getAttribute('href')))
    .filter(Boolean);

  const onScroll = () => {
    const y = window.scrollY || 0;
    nav?.classList.toggle('is-stuck', y > 12);
    toTop?.classList.toggle('is-on', y > 480);
    const height = document.documentElement.scrollHeight - window.innerHeight;
    if (progress) progress.style.width = `${height > 0 ? (y / height) * 100 : 0}%`;

    let active = sections[0];
    sections.forEach((section) => {
      if (section.offsetTop - 140 <= y) active = section;
    });
    links.forEach((a) => a.classList.toggle('is-active', active && a.getAttribute('href') === `#${active.id}`));
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  toTop?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  const toggle = $('#navToggle');
  const navLinks = $('#navLinks');
  toggle?.addEventListener('click', () => {
    const open = navLinks.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
  navLinks?.addEventListener('click', (event) => {
    if (event.target.tagName === 'A') {
      navLinks.classList.remove('is-open');
      toggle?.setAttribute('aria-expanded', 'false');
    }
  });
}

/* ---------------- 启动 ---------------- */
async function boot() {
  setupScrollUi();
  setupMessageForm();
  await trackVisit();

  try {
    // 标准库后端会把数据内联为 window.__SITE_DATA__，此时省掉一次请求
    const bootstrap = window.__SITE_DATA__;
    const [resume, skills] = bootstrap
      ? [bootstrap.resume, bootstrap.skills]
      : await Promise.all([api('/api/resume'), api('/api/skills')]);
    renderProfile(resume.profile);
    renderEducation(resume.education, resume.education[0]?.courses);
    renderExperience(resume.experience);
    renderProjects(resume.projects);
    renderSkills(skills.skills, skills.learning);
    renderCampus(resume.campus, resume.about);
    observeReveal();
  } catch (err) {
    console.error(err);
    showToast(`简历数据加载失败：${err.message}`);
  }

  loadMessages(1);
}

document.addEventListener('DOMContentLoaded', boot);
