const STATE = {
  data: null,
  filtered: null,
  currentCategory: null,
  currentItem: null,
  currentFile: {
    path: null,
    text: null,
    isJson: false,
    isMarkdown: false,
    renderRaw: false,
  },
};

async function loadIndex() {
  const res = await fetch('data/models_index.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to load index: ${res.status}`);
  return res.json();
}

function renderCategories(items) {
  const byCat = Array.from(new Set(items.map(x => x.category))).sort();
  const nav = document.getElementById('categoryNav');
  nav.innerHTML = '';
  byCat.forEach(cat => {
    const btn = document.createElement('button');
    btn.textContent = cat;
    btn.className = 'cat-btn';
    btn.onclick = () => {
      STATE.currentCategory = cat;
      document.querySelectorAll('.categories button').forEach(b => b.classList.toggle('active', b === btn));
      renderList();
    };
    nav.appendChild(btn);
  });
}

function renderList() {
  const listEl = document.getElementById('listView');
  const search = document.getElementById('searchInput').value.trim().toLowerCase();
  const items = STATE.filtered ?? STATE.data.items;
  // Global search: if search is present, ignore category filter
  let visible = items.filter(x => {
    const hay = `${x.category} ${x.model} ${x.title ?? ''} ${(x.tags ?? []).join(' ')} ${x.summary ?? ''}`.toLowerCase();
    const matchesSearch = search.length === 0 || hay.includes(search);
    const matchesCategory = !STATE.currentCategory || x.category === STATE.currentCategory;
    return search.length > 0 ? matchesSearch : (matchesCategory && matchesSearch);
  });
  // Sort A→Z by display title, fallback to model
  visible = visible.sort((a, b) => {
    const ta = (a.title || a.model || '').toLowerCase();
    const tb = (b.title || b.model || '').toLowerCase();
    if (ta < tb) return -1;
    if (ta > tb) return 1;
    return 0;
  });

  listEl.innerHTML = '';
  document.getElementById('detailView').classList.add('hidden');

  visible.forEach(it => {
    const card = document.createElement('div');
    card.className = 'card';
    const title = it.title || it.model;
    card.innerHTML = `
      <h3>${title}</h3>
      <p>${it.summary ?? ''}</p>
      <div class="tags">${(it.tags ?? []).map(t => `<span class="tag">${t}</span>`).join('')}</div>
    `;
    card.onclick = () => showDetail(it);
    listEl.appendChild(card);
  });
}

function showDetail(item) {
  STATE.currentItem = item;
  document.getElementById('listView').innerHTML = '';
  const detail = document.getElementById('detailView');
  detail.classList.remove('hidden');
  document.getElementById('detailTitle').textContent = item.title || item.model;
  document.getElementById('detailSummary').textContent = item.summary ?? '';
  document.getElementById('detailMeta').textContent = `${item.category} / ${item.model}`;

  const filesEl = document.getElementById('detailFiles');
  filesEl.innerHTML = '';
  const paths = item.paths || {};
  const entries = Object.entries(paths);

  const jsonEntries = entries.filter(([, p]) => p.endsWith('.json'));
  const mdEntries = entries.filter(([, p]) => p.endsWith('.md'));

  const jsonCol = document.createElement('div');
  jsonCol.className = 'files-col';
  const jsonTitle = document.createElement('div');
  jsonTitle.className = 'files-col-title';
  jsonTitle.textContent = 'JSON';
  jsonCol.appendChild(jsonTitle);
  if (jsonEntries.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'files-empty';
    empty.textContent = '—';
    jsonCol.appendChild(empty);
  } else {
    jsonEntries.forEach(([key, path]) => {
      const btn = document.createElement('button');
      btn.className = 'file-btn';
      btn.textContent = key;
      btn.onclick = () => loadFile(path);
      jsonCol.appendChild(btn);
    });
  }

  const mdCol = document.createElement('div');
  mdCol.className = 'files-col';
  const mdTitle = document.createElement('div');
  mdTitle.className = 'files-col-title';
  mdTitle.textContent = 'Markdown';
  mdCol.appendChild(mdTitle);
  if (mdEntries.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'files-empty';
    empty.textContent = '—';
    mdCol.appendChild(empty);
  } else {
    mdEntries.forEach(([key, path]) => {
      const btn = document.createElement('button');
      btn.className = 'file-btn';
      btn.textContent = key;
      btn.onclick = () => loadFile(path);
      mdCol.appendChild(btn);
    });
  }

  filesEl.appendChild(jsonCol);
  filesEl.appendChild(mdCol);

  // Prefer opening prompting first (if present), else first md, else first json, else any file
  let defaultPath = null;
  if (paths.prompting) defaultPath = paths.prompting;
  if (!defaultPath && mdEntries.length > 0) defaultPath = mdEntries[0][1];
  if (!defaultPath && jsonEntries.length > 0) defaultPath = jsonEntries[0][1];
  if (!defaultPath && entries.length > 0) defaultPath = entries[0][1];
  if (defaultPath) loadFile(defaultPath);
}

function escapeHtml(text) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function highlightJson(text) {
  let obj;
  try {
    obj = JSON.parse(text);
  } catch (e) {
    return `<pre class="code-block">${escapeHtml(text)}</pre>`;
  }
  const pretty = JSON.stringify(obj, null, 2);
  const html = escapeHtml(pretty)
    .replace(/(".*?")(?=\s*:)/g, '<span class="json-key">$1</span>')
    .replace(/:\s*(".*?")/g, ': <span class="json-string">$1</span>')
    .replace(/:\s*(\b-?\d+(?:\.\d+)?\b)/g, ': <span class="json-number">$1</span>')
    .replace(/:\s*(\btrue\b|\bfalse\b)/g, ': <span class="json-boolean">$1</span>')
    .replace(/:\s*(\bnull\b)/g, ': <span class="json-null">$1</span>');
  return `<pre class="code-block json">${html}</pre>`;
}

function renderMarkdown(md) {
  const escape = (s) => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  let html = md.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre class="code-block"><code class="lang-${escape(lang)}">${escape(code)}</code></pre>`;
  });
  html = html.replace(/`([^`]+)`/g, (_, code) => `<code>${escape(code)}</code>`);
  html = html.replace(/^######\s+(.*)$/gm, '<h6>$1</h6>')
             .replace(/^#####\s+(.*)$/gm, '<h5>$1</h5>')
             .replace(/^####\s+(.*)$/gm, '<h4>$1</h4>')
             .replace(/^###\s+(.*)$/gm, '<h3>$1</h3>')
             .replace(/^##\s+(.*)$/gm, '<h2>$1</h2>')
             .replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
             .replace(/\*(.+?)\*/g, '<em>$1</em>')
             .replace(/_(.+?)_/g, '<em>$1</em>');
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1<\/a>');
  html = html.replace(/^(?:- |\* )(.*(?:\n(?:- |\* ).*)*)/gm, (m) => {
    const items = m.split(/\n/).map(line => line.replace(/^(?:- |\* )/, '').trim()).filter(Boolean);
    return `<ul>${items.map(it => `<li>${it}</li>`).join('')}</ul>`;
  });
  const lines = html.split(/\n\n+/).map(block => {
    if (/^\s*<\/?(h\d|ul|pre|blockquote|table|p|code)/i.test(block)) return block;
    return `<p>${block.replaceAll('\n', '<br/>')}</p>`;
  });
  return lines.join('\n');
}

async function loadFile(path) {
  const contentEl = document.getElementById('fileContent');
  contentEl.textContent = 'Loading...';
  const sitePath = path.startsWith('/models/') ? `models/${path.slice('/models/'.length)}` : path;
  try {
    const res = await fetch(sitePath, { cache: 'no-store' });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const text = await res.text();
    STATE.currentFile = {
      path,
      text,
      isJson: path.endsWith('.json'),
      isMarkdown: path.endsWith('.md'),
      renderRaw: false,
    };
    renderFileContent();
  } catch (e) {
    contentEl.textContent = `Failed to load file: ${e.message}`;
  }
}

function renderJsonTreeHTML(value, key = null) {
  const type = Array.isArray(value) ? 'array' : (value === null ? 'null' : typeof value);
  if (type === 'object' || type === 'array') {
    const entries = type === 'array' ? value.map((v, i) => [i, v]) : Object.entries(value);
    const label = key !== null ? `${key} ${type === 'array' ? `[${entries.length}]` : ''}` : (type === 'array' ? `Array [${entries.length}]` : 'Object');
    return `<details open><summary>${escapeHtml(String(label))}</summary><ul class="json-tree">${entries.map(([k, v]) => `<li>${renderJsonTreeHTML(v, k)}</li>`).join('')}</ul></details>`;
  }
  let cls = 'json-primitive';
  if (type === 'string') cls = 'json-string';
  else if (type === 'number') cls = 'json-number';
  else if (type === 'boolean') cls = 'json-boolean';
  else if (type === 'null') cls = 'json-null';
  const safe = escapeHtml(type === 'string' ? `"${value}"` : String(value));
  return key !== null
    ? `<span class="json-key">${escapeHtml(String(key))}</span>: <span class="${cls}">${safe}</span>`
    : `<span class="${cls}">${safe}</span>`;
}

function renderFileContent() {
  const { path, text, isJson, isMarkdown, renderRaw } = STATE.currentFile;
  const contentEl = document.getElementById('fileContent');
  if (!path) { contentEl.textContent = ''; return; }

  const toolbar = `<div class="file-toolbar"><span class="file-name">${escapeHtml(path)}</span>${(isJson || isMarkdown) ? `<button id=\"toggleRawBtn\" class=\"toggle-raw\">${renderRaw ? 'Show rendered' : 'Show raw'}</button>` : ''}</div>`;

  let bodyHtml = '';
  if (renderRaw || (!isJson && !isMarkdown)) {
    bodyHtml = `<pre class="code-block">${escapeHtml(text)}</pre>`;
  } else if (isJson) {
    try {
      const obj = JSON.parse(text);
      bodyHtml = `<div class="json-tree-root">${renderJsonTreeHTML(obj)}</div>`;
    } catch {
      bodyHtml = highlightJson(text);
    }
  } else if (isMarkdown) {
    bodyHtml = renderMarkdown(text);
  }

  if (renderRaw) {
    contentEl.innerHTML = `${toolbar}${bodyHtml}`;
  } else {
    contentEl.innerHTML = `${toolbar}<div class="content-inner">${bodyHtml}</div>`;
  }
  const toggle = document.getElementById('toggleRawBtn');
  if (toggle) {
    toggle.addEventListener('click', () => {
      STATE.currentFile.renderRaw = !STATE.currentFile.renderRaw;
      renderFileContent();
    });
  }
}

function wireSearch() {
  const input = document.getElementById('searchInput');
  input.addEventListener('input', () => renderList());
}

function wireBack() {
  document.getElementById('backButton').onclick = () => {
    STATE.currentItem = null;
    document.getElementById('detailView').classList.add('hidden');
    renderList();
  };
}

(function wireHomeLink(){
  const home = document.getElementById('siteHome');
  if (!home) return;
  home.addEventListener('click', () => {
    STATE.currentCategory = null;
    STATE.currentItem = null;
    const search = document.getElementById('searchInput');
    if (search) search.value = '';
    document.getElementById('detailView').classList.add('hidden');
    document.querySelectorAll('.categories button').forEach(b => b.classList.remove('active'));
    renderList();
  });
})();

(function wireHomeImage(){
  const homeImg = document.getElementById('siteHomeImg');
  if (!homeImg) return;
  homeImg.addEventListener('click', (e) => {
    e.preventDefault();
    STATE.currentCategory = null;
    STATE.currentItem = null;
    const search = document.getElementById('searchInput');
    if (search) search.value = '';
    document.getElementById('detailView').classList.add('hidden');
    document.querySelectorAll('.categories button').forEach(b => b.classList.remove('active'));
    renderList();
  });
})();

(async function init() {
  try {
    STATE.data = await loadIndex();
    document.getElementById('generatedAt').textContent = `Generated: ${STATE.data.generatedAt ?? ''}`;
    renderCategories(STATE.data.items);
    wireSearch();
    wireBack();
    renderList();
    // Theme toggle
    const root = document.documentElement;
    const savedTheme = localStorage.getItem('scapo_theme');
    if (savedTheme) root.setAttribute('data-theme', savedTheme);
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
      const splitCircleSvg = (leftColor, rightColor) => {
        return `\n<svg class="theme-icon" width="22" height="22" viewBox="0 0 20 20" aria-hidden="true">\n  <defs>\n    <clipPath id="splitCircleClip">\n      <circle cx="10" cy="10" r="9"/>\n    </clipPath>\n  </defs>\n  <g clip-path="url(#splitCircleClip)">\n    <rect x="0" y="0" width="10" height="20" fill="${leftColor}"/>\n    <rect x="10" y="0" width="10" height="20" fill="${rightColor}"/>\n  </g>\n  <circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" stroke-width="1"/>\n</svg>`;
      };
      const updateIcon = () => {
        const th = root.getAttribute('data-theme') || 'dark';
        // Dark theme (night): left dark, right light. Light theme (day): left light, right dark.
        const darkCol = '#0f172a';
        const lightCol = '#ffffff';
        toggle.innerHTML = th === 'light' ? splitCircleSvg(lightCol, darkCol) : splitCircleSvg(darkCol, lightCol);
      };
      updateIcon();
      toggle.addEventListener('click', () => {
        const current = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        root.setAttribute('data-theme', current);
        localStorage.setItem('scapo_theme', current);
        updateIcon();
      });
    }
    try {
      const r = await fetch('https://api.github.com/repos/czero-cc/SCAPO');
      if (r.ok) {
        const j = await r.json();
        const stars = document.getElementById('ghStars');
        if (stars && typeof j.stargazers_count === 'number') {
          stars.textContent = `${j.stargazers_count.toLocaleString()} ⭐`;
        }
      }
    } catch (_) { /* ignore */ }
  } catch (e) {
    const listEl = document.getElementById('listView');
    listEl.innerHTML = `<div class="card">Failed to initialize: ${e.message}. Ensure data/models_index.json exists.</div>`;
  }
})();


