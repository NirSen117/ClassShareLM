/* ============================================================
   ClassShareLM — Frontend Application
   API client, tab system, form handlers, rendering
   ============================================================ */

(function () {
  'use strict';

  // ---- Configuration ----
  const API_BASE = window.location.origin;

  // ---- DOM Helpers ----
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ---- Toast Notifications ----
  function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = {
      success: '✓',
      error: '✕',
      info: 'ℹ',
    };
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 4200);
  }

  // ---- Escape HTML ----
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ---- Simple Markdown to HTML ----
  function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    // Code blocks
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Unordered lists
    html = html.replace(/^[-•] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Ordered lists
    html = html.replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>');

    // Line breaks for remaining lines
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br/>');

    // Wrap in paragraph if needed
    if (!html.startsWith('<')) {
      html = '<p>' + html + '</p>';
    }

    return html;
  }

  // ---- Sources Table ----
  function renderSources(sources) {
    if (!sources || sources.length === 0) return '';
    let html = `<div class="sources-section">
      <p class="sources-title">📄 Sources</p>
      <table class="sources-table">
        <thead><tr><th>File</th><th>Page</th><th>Chunk</th><th>Score</th></tr></thead>
        <tbody>`;
    for (const s of sources) {
      html += `<tr>
        <td>${escapeHtml(s.filename || '')}</td>
        <td>${s.page}</td>
        <td>${s.chunk_index}</td>
        <td>${typeof s.score === 'number' ? s.score.toFixed(4) : s.score}</td>
      </tr>`;
    }
    html += '</tbody></table></div>';
    return html;
  }

  // ---- Loading Skeleton ----
  function showSkeleton(container) {
    container.hidden = false;
    container.innerHTML = `
      <div class="skeleton skeleton-lg"></div>
      <div class="skeleton skeleton-md"></div>
      <div class="skeleton skeleton-md"></div>
      <div class="skeleton skeleton-sm"></div>
      <div class="skeleton skeleton-md"></div>
    `;
  }

  // ---- Result Renderer ----
  function renderResult(container, data) {
    container.hidden = false;
    const badge = data.cached
      ? '<span class="result-badge badge-cached">Cached</span>'
      : '<span class="result-badge badge-fresh">Fresh</span>';
    container.innerHTML = `
      ${badge}
      <div class="result-content">${renderMarkdown(data.content)}</div>
      ${renderSources(data.sources)}
    `;
  }

  // ---- Button Loading State ----
  function setLoading(btn, loading) {
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');
    if (loading) {
      btn.disabled = true;
      if (text) text.hidden = true;
      if (loader) loader.hidden = false;
    } else {
      btn.disabled = false;
      if (text) text.hidden = false;
      if (loader) loader.hidden = true;
    }
  }

  // ---- API Client ----
  async function apiPost(endpoint, body) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  async function apiGet(endpoint, params = {}) {
    const url = new URL(`${API_BASE}${endpoint}`);
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
    }
    const res = await fetch(url.toString());
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  async function apiUpload(file, year, subject) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('year', year);
    formData.append('subject', subject);
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  }

  // ---- Get year/subject values ----
  function getYear() { return ($('#input-year').value || '').trim(); }
  function getSubject() { return ($('#input-subject').value || '').trim(); }

  function validateSubject() {
    const year = getYear();
    const subject = getSubject();
    if (!year || !subject) {
      showToast('Please set Academic Year and Subject in the sidebar.', 'error');
      return false;
    }
    return true;
  }

  // ================================================================
  //  INIT
  // ================================================================
  document.addEventListener('DOMContentLoaded', () => {

    // ---- Tab Navigation ----
    const tabBtns = $$('.tab-btn');
    const tabPanels = $$('.tab-panel');

    tabBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        tabBtns.forEach((b) => { b.classList.remove('active'); b.setAttribute('aria-selected', 'false'); });
        tabPanels.forEach((p) => p.classList.remove('active'));
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        const panel = $(`#panel-${target}`);
        if (panel) panel.classList.add('active');
      });
    });

    // ---- Sidebar Toggle (mobile) ----
    const sidebarToggle = $('#sidebar-toggle');
    const sidebar = $('#sidebar');
    if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
      // Close sidebar when clicking outside on mobile
      document.addEventListener('click', (e) => {
        if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
          sidebar.classList.remove('open');
        }
      });
    }

    // ---- Load Subjects ----
    async function loadSubjects() {
      try {
        const data = await apiGet('/subjects');
        const list = $('#subject-list');
        const items = data.items || [];
        if (items.length === 0) {
          list.innerHTML = '<span class="chip-placeholder">No subjects yet — upload a PDF to start</span>';
          return;
        }
        list.innerHTML = '';
        for (const s of items) {
          const chip = document.createElement('button');
          chip.className = 'chip';
          chip.textContent = `${s.subject} (${s.year})`;
          chip.addEventListener('click', () => {
            $('#input-year').value = s.year;
            $('#input-subject').value = s.subject;
            $$('.chip').forEach((c) => c.classList.remove('active'));
            chip.classList.add('active');
            showToast(`Selected: ${s.subject} — ${s.year}`, 'info');
          });
          list.appendChild(chip);
        }
      } catch (err) {
        $('#subject-list').innerHTML = '<span class="chip-placeholder">Could not load subjects</span>';
      }
    }
    loadSubjects();

    // ---- PDF Upload ----
    const dropZone = $('#drop-zone');
    const fileInput = $('#file-input');
    const fileNameEl = $('#file-name');
    const btnUpload = $('#btn-upload');
    const uploadProgress = $('#upload-progress');
    let selectedFile = null;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      const files = e.dataTransfer.files;
      if (files.length > 0 && files[0].name.toLowerCase().endsWith('.pdf')) {
        selectedFile = files[0];
        fileNameEl.textContent = selectedFile.name;
        btnUpload.disabled = false;
      } else {
        showToast('Please drop a PDF file.', 'error');
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        selectedFile = fileInput.files[0];
        fileNameEl.textContent = selectedFile.name;
        btnUpload.disabled = false;
      }
    });

    btnUpload.addEventListener('click', async () => {
      if (!selectedFile) {
        showToast('Select a PDF first.', 'error');
        return;
      }
      if (!validateSubject()) return;

      btnUpload.disabled = true;
      btnUpload.textContent = 'Uploading...';
      uploadProgress.hidden = false;

      try {
        const result = await apiUpload(selectedFile, getYear(), getSubject());
        showToast(result.message || 'Document uploaded and indexed!', 'success');
        selectedFile = null;
        fileNameEl.textContent = '';
        fileInput.value = '';
        loadSubjects();
      } catch (err) {
        showToast(`Upload failed: ${err.message}`, 'error');
      } finally {
        btnUpload.disabled = false;
        btnUpload.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
          Upload &amp; Index`;
        uploadProgress.hidden = true;
      }
    });

    // ---- ASK ----
    const btnAsk = $('#btn-ask');
    btnAsk.addEventListener('click', async () => {
      if (!validateSubject()) return;
      const question = $('#ask-question').value.trim();
      if (!question) { showToast('Enter a question.', 'error'); return; }

      const resultEl = $('#result-ask');
      showSkeleton(resultEl);
      setLoading(btnAsk, true);

      try {
        const data = await apiPost('/generate/ask', {
          year: getYear(),
          subject: getSubject(),
          question,
          explanation_mode: $('#ask-explain').checked,
        });
        renderResult(resultEl, data);
      } catch (err) {
        resultEl.hidden = false;
        resultEl.innerHTML = `<p style="color:var(--error)">Error: ${escapeHtml(err.message)}</p>`;
        showToast(err.message, 'error');
      } finally {
        setLoading(btnAsk, false);
      }
    });

    // ---- SUMMARY ----
    const btnSummary = $('#btn-summary');
    btnSummary.addEventListener('click', async () => {
      if (!validateSubject()) return;

      const resultEl = $('#result-summary');
      showSkeleton(resultEl);
      setLoading(btnSummary, true);

      try {
        const data = await apiPost('/generate/summary', {
          year: getYear(),
          subject: getSubject(),
          focus: $('#summary-focus').value.trim() || null,
        });
        renderResult(resultEl, data);
      } catch (err) {
        resultEl.hidden = false;
        resultEl.innerHTML = `<p style="color:var(--error)">Error: ${escapeHtml(err.message)}</p>`;
        showToast(err.message, 'error');
      } finally {
        setLoading(btnSummary, false);
      }
    });

    // ---- NOTES ----
    const btnNotes = $('#btn-notes');
    btnNotes.addEventListener('click', async () => {
      if (!validateSubject()) return;

      const resultEl = $('#result-notes');
      showSkeleton(resultEl);
      setLoading(btnNotes, true);

      try {
        const data = await apiPost('/generate/notes', {
          year: getYear(),
          subject: getSubject(),
          focus: $('#notes-focus').value.trim() || null,
        });
        renderResult(resultEl, data);
      } catch (err) {
        resultEl.hidden = false;
        resultEl.innerHTML = `<p style="color:var(--error)">Error: ${escapeHtml(err.message)}</p>`;
        showToast(err.message, 'error');
      } finally {
        setLoading(btnNotes, false);
      }
    });

    // ---- QUIZ ----
    const btnQuiz = $('#btn-quiz');
    btnQuiz.addEventListener('click', async () => {
      if (!validateSubject()) return;
      const topic = $('#quiz-topic').value.trim();
      if (!topic) { showToast('Enter a quiz topic.', 'error'); return; }

      const resultEl = $('#result-quiz');
      showSkeleton(resultEl);
      setLoading(btnQuiz, true);

      try {
        const data = await apiPost('/generate/quiz', {
          year: getYear(),
          subject: getSubject(),
          topic,
          difficulty: $('#quiz-difficulty').value,
          num_questions: parseInt($('#quiz-num').value, 10) || 5,
        });
        renderResult(resultEl, data);
      } catch (err) {
        resultEl.hidden = false;
        resultEl.innerHTML = `<p style="color:var(--error)">Error: ${escapeHtml(err.message)}</p>`;
        showToast(err.message, 'error');
      } finally {
        setLoading(btnQuiz, false);
      }
    });

    // ---- FEED ----
    const btnFeed = $('#btn-feed');
    btnFeed.addEventListener('click', async () => {
      const feedArea = $('#result-feed');
      feedArea.innerHTML = `
        <div class="skeleton skeleton-lg"></div>
        <div class="skeleton skeleton-md"></div>
        <div class="skeleton skeleton-md"></div>
      `;

      try {
        const data = await apiGet('/feed', {
          year: getYear(),
          subject: getSubject(),
          limit: 50,
        });
        const items = data.items || [];
        if (items.length === 0) {
          feedArea.innerHTML = `
            <div class="feed-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <p>No generated content yet.<br/>Upload documents and start generating!</p>
            </div>`;
          return;
        }

        feedArea.innerHTML = '';
        for (const item of items) {
          const typeClass = `feed-type-${item.content_type}`;
          const date = item.created_at ? new Date(item.created_at).toLocaleString() : '';
          const feedEl = document.createElement('div');
          feedEl.className = 'feed-item';
          feedEl.innerHTML = `
            <div class="feed-header">
              <span class="feed-type-badge ${typeClass}">${escapeHtml(item.content_type)}</span>
              <span class="feed-meta">${escapeHtml(item.subject)} · ${escapeHtml(item.year)} · ${date}</span>
              ${item.is_cached ? '<span class="result-badge badge-cached" style="margin:0">Cached</span>' : ''}
            </div>
            ${item.query_text ? `<p class="feed-query">"${escapeHtml(item.query_text)}"</p>` : ''}
            <div class="feed-content" id="feed-content-${item.id}">
              ${renderMarkdown(item.content)}
            </div>
            <button class="feed-expand" data-target="feed-content-${item.id}">Show more ▾</button>
            ${renderSources(item.sources)}
          `;
          feedArea.appendChild(feedEl);
        }

        // Expand/collapse
        feedArea.querySelectorAll('.feed-expand').forEach((btn) => {
          btn.addEventListener('click', () => {
            const target = document.getElementById(btn.dataset.target);
            if (target) {
              const isExpanded = target.classList.toggle('expanded');
              btn.textContent = isExpanded ? 'Show less ▴' : 'Show more ▾';
            }
          });
        });
      } catch (err) {
        feedArea.innerHTML = `<p style="color:var(--error)">Error loading feed: ${escapeHtml(err.message)}</p>`;
        showToast(err.message, 'error');
      }
    });

    // ---- Auto-load feed on tab switch ----
    const feedTab = $('#tab-feed');
    if (feedTab) {
      feedTab.addEventListener('click', () => {
        setTimeout(() => btnFeed.click(), 100);
      });
    }

  }); // end DOMContentLoaded
})();
