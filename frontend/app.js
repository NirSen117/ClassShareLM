/* ============================================================
   ClassShareLM — Frontend Application v2
   Firebase Auth, Sections, Personal/Public Feed
   ============================================================ */

(function () {
  'use strict';

  // ---- Configuration ----
  const API_BASE = window.location.origin;

  // Firebase is initialized in index.html — just reference the auth instance
  const auth = window.firebaseAuth;

  // ---- DOM Helpers ----
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ---- State ----
  let currentUser = null;   // Firebase user object
  let idToken = null;        // Firebase ID token

  // ---- Toast Notifications ----
  function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 4200);
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
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => `<pre><code>${code.trim()}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/^[-•] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
    html = html.replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>');
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br/>');
    if (!html.startsWith('<')) html = '<p>' + html + '</p>';
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

  // ---- Auth Headers ----
  function authHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (idToken) headers['Authorization'] = `Bearer ${idToken}`;
    return headers;
  }

  // Helper to ensure we have a fresh ID token (force refresh when needed)
  async function ensureIdToken(force = false) {
    if (currentUser) {
      try {
        idToken = await currentUser.getIdToken(force);
      } catch (e) {
        console.warn('Failed to refresh ID token', e);
        idToken = null;
      }
    }
    return idToken;
  }

  // Generic fetch wrapper that retries once after refreshing token on 401
  async function authFetch(input, init = {}) {
    // Attach current token if available
    init.headers = Object.assign({}, init.headers || {}, authHeaders());
    let res = await fetch(input, init);
    if (res.status === 401) {
      // Try to refresh token and retry once
      await ensureIdToken(true);
      init.headers = Object.assign({}, init.headers || {}, authHeaders());
      res = await fetch(input, init);
    }
    return res;
  }

  async function apiPost(endpoint, body) {
    const res = await authFetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: Object.assign({}, { 'Content-Type': 'application/json' }),
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
    const res = await authFetch(url.toString(), {});
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  async function apiUpload(file, year, section, subject) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('year', year);
    formData.append('section', section);
    formData.append('subject', subject);
    const headers = {};
    if (idToken) headers['Authorization'] = `Bearer ${idToken}`;
    // Use authFetch so a 401 triggers a token refresh + retry
    const res = await authFetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  }

  // ---- Get form values ----
  function getYear() { return ($('#input-year').value || '').trim(); }
  function getSection() {
    const sel = $('#input-section');
    return sel ? (sel.value || '').trim() : '';
  }
  function getSubject() { return ($('#input-subject').value || '').trim(); }

  function validateConfig() {
    if (!getYear() || !getSection() || !getSubject()) {
      showToast('Please set Year, Section, and Subject in the sidebar.', 'error');
      return false;
    }
    return true;
  }

  // ---- User Avatar Helper ----
  function getInitial(name) {
    if (!name) return '?';
    return name.charAt(0).toUpperCase();
  }

  // ================================================================
  //  FIREBASE AUTH
  // ================================================================
  function setupAuth() {
    const auth = window.firebaseAuth;
    if (!auth) {
      console.warn('Firebase Auth not initialized');
      return;
    }

    const overlay = $('#auth-overlay');
    const appMain = $('#app-main');
    const loginForm = $('#auth-login');
    const registerForm = $('#auth-register');

    // Toggle between login/register
    $('#show-register').addEventListener('click', (e) => {
      e.preventDefault();
      loginForm.hidden = true;
      registerForm.hidden = false;
    });

    $('#show-login').addEventListener('click', (e) => {
      e.preventDefault();
      registerForm.hidden = true;
      loginForm.hidden = false;
    });

    // Email/Password Login
    $('#btn-login').addEventListener('click', async () => {
      const email = $('#login-email').value.trim();
      const password = $('#login-password').value;
      if (!email || !password) {
        showToast('Please enter email and password.', 'error');
        return;
      }
      const btn = $('#btn-login');
      setLoading(btn, true);
      try {
        await auth.signInWithEmailAndPassword(email, password);
      } catch (err) {
        showToast(friendlyAuthError(err), 'error');
      } finally {
        setLoading(btn, false);
      }
    });

    // Email/Password Register
    $('#btn-register').addEventListener('click', async () => {
      const name = $('#register-name').value.trim();
      const email = $('#register-email').value.trim();
      const password = $('#register-password').value;
      if (!name || !email || !password) {
        showToast('Please fill in all fields.', 'error');
        return;
      }
      if (password.length < 6) {
        showToast('Password must be at least 6 characters.', 'error');
        return;
      }
      const btn = $('#btn-register');
      setLoading(btn, true);
      try {
        const cred = await auth.createUserWithEmailAndPassword(email, password);
        await cred.user.updateProfile({ displayName: name });
      } catch (err) {
        showToast(friendlyAuthError(err), 'error');
      } finally {
        setLoading(btn, false);
      }
    });

    // Google Sign-In
    const googleProvider = new firebase.auth.GoogleAuthProvider();

    async function signInWithGoogle() {
      try {
        await auth.signInWithPopup(googleProvider);
      } catch (err) {
        // Fallback: some hosts (Spaces, embedded iframes) block popups.
        // In that case use redirect-based sign-in which works more reliably.
        if (err.code === 'auth/popup-blocked' || err.code === 'auth/operation-not-supported-in-this-environment' || err.message?.toLowerCase().includes('popup')) {
          try {
            await auth.signInWithRedirect(googleProvider);
            return;
          } catch (redirErr) {
            console.error('Redirect sign-in failed', redirErr);
            showToast(friendlyAuthError(redirErr), 'error');
            return;
          }
        }
        showToast(friendlyAuthError(err), 'error');
      }
    }

    $('#btn-google').addEventListener('click', async () => {
      await signInWithGoogle();
    });

    $('#btn-google-register').addEventListener('click', async () => {
      await signInWithGoogle();
    });

    // Logout
    $('#btn-logout').addEventListener('click', async () => {
      try {
        await auth.signOut();
        showToast('Signed out successfully.', 'info');
      } catch (err) {
        showToast('Sign out failed.', 'error');
      }
    });

    // Auth State Observer
    auth.onAuthStateChanged(async (user) => {
      if (user) {
        currentUser = user;
        try {
          idToken = await user.getIdToken();
        } catch (e) {
          idToken = null;
        }
        // Update UI
        const displayName = user.displayName || user.email.split('@')[0];
        $('#user-avatar').textContent = getInitial(displayName);
        $('#user-name').textContent = displayName;

        overlay.classList.add('hidden');
        appMain.hidden = false;

        // Load data
        loadSections();
        loadSubjects();

        showToast(`Welcome, ${displayName}!`, 'success');

        // Refresh token periodically (every 50 min)
        setInterval(async () => {
          try {
            idToken = await user.getIdToken(true);
          } catch (e) { /* ignore */ }
        }, 50 * 60 * 1000);

      } else {
        currentUser = null;
        idToken = null;
        overlay.classList.remove('hidden');
        appMain.hidden = true;
      }
    });
  }

  function friendlyAuthError(err) {
    const map = {
      'auth/email-already-in-use': 'This email is already registered. Try signing in.',
      'auth/invalid-email': 'Invalid email address.',
      'auth/user-not-found': 'No account found with this email.',
      'auth/wrong-password': 'Incorrect password.',
      'auth/weak-password': 'Password must be at least 6 characters.',
      'auth/too-many-requests': 'Too many attempts. Please try again later.',
      'auth/popup-closed-by-user': 'Sign-in popup was closed.',
      'auth/network-request-failed': 'Network error. Check your connection.',
    };
    return map[err.code] || err.message || 'Authentication error.';
  }

  // ================================================================
  //  SECTIONS
  // ================================================================
  async function loadSections() {
    const year = getYear();
    if (!year) return;
    try {
      const data = await apiGet('/sections', { year });
      const select = $('#input-section');
      const currentVal = select.value;
      select.innerHTML = '<option value="">— Select or create —</option>';
      for (const s of (data.items || [])) {
        const opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = s.name;
        select.appendChild(opt);
      }
      if (currentVal) select.value = currentVal;
    } catch (err) {
      console.error('Error loading sections:', err);
    }
  }

  // ================================================================
  //  INIT
  // ================================================================
  document.addEventListener('DOMContentLoaded', () => {

    // ---- Firebase Auth ----
    setupAuth();

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
      sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
      document.addEventListener('click', (e) => {
        if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
          sidebar.classList.remove('open');
        }
      });
    }

    // ---- Year change → reload sections ----
    const yearInput = $('#input-year');
    let yearTimeout;
    yearInput.addEventListener('input', () => {
      clearTimeout(yearTimeout);
      yearTimeout = setTimeout(() => {
        loadSections();
        loadSubjects();
      }, 500);
    });

    // ---- Section change → reload subjects ----
    const sectionSelect = $('#input-section');
    sectionSelect.addEventListener('change', () => {
      loadSubjects();
    });

    // ---- Add Section ----
    $('#btn-add-section').addEventListener('click', async () => {
      const year = getYear();
      if (!year) {
        showToast('Set Academic Year first.', 'error');
        return;
      }
      const name = prompt('Enter new section name (e.g. Section A):');
      if (!name || !name.trim()) return;

      try {
        await apiPost('/sections/upsert', { year, name: name.trim() });
        showToast(`Section "${name.trim()}" created!`, 'success');
        await loadSections();
        sectionSelect.value = name.trim();
        loadSubjects();
      } catch (err) {
        showToast(`Failed: ${err.message}`, 'error');
      }
    });

    // ---- Load Subjects ----
    async function loadSubjects() {
      const list = $('#subject-list');
      const year = getYear();
      const section = getSection();

      if (!year || !section) {
        list.innerHTML = '<span class="chip-placeholder">Select year and section first</span>';
        return;
      }

      try {
        const data = await apiGet('/subjects', { year, section });
        const items = data.items || [];
        if (items.length === 0) {
          list.innerHTML = '<span class="chip-placeholder">No subjects yet — upload a PDF to start</span>';
          return;
        }
        list.innerHTML = '';
        for (const s of items) {
          const chip = document.createElement('button');
          chip.className = 'chip';
          chip.textContent = s.subject;
          chip.addEventListener('click', () => {
            $('#input-subject').value = s.subject;
            $$('.chip').forEach((c) => c.classList.remove('active'));
            chip.classList.add('active');
            showToast(`Selected: ${s.subject}`, 'info');
          });
          list.appendChild(chip);
        }
      } catch (err) {
        list.innerHTML = '<span class="chip-placeholder">Could not load subjects</span>';
      }
    }

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
      if (!selectedFile) { showToast('Select a PDF first.', 'error'); return; }
      if (!validateConfig()) return;

      btnUpload.disabled = true;
      btnUpload.textContent = 'Uploading...';
      uploadProgress.hidden = false;

      try {
        const result = await apiUpload(selectedFile, getYear(), getSection(), getSubject());
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
      if (!validateConfig()) return;
      const question = $('#ask-question').value.trim();
      if (!question) { showToast('Enter a question.', 'error'); return; }

      const resultEl = $('#result-ask');
      showSkeleton(resultEl);
      setLoading(btnAsk, true);

      try {
        const data = await apiPost('/generate/ask', {
          year: getYear(),
          section: getSection(),
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
      if (!validateConfig()) return;

      const resultEl = $('#result-summary');
      showSkeleton(resultEl);
      setLoading(btnSummary, true);

      try {
        const data = await apiPost('/generate/summary', {
          year: getYear(),
          section: getSection(),
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
      if (!validateConfig()) return;

      const resultEl = $('#result-notes');
      showSkeleton(resultEl);
      setLoading(btnNotes, true);

      try {
        const data = await apiPost('/generate/notes', {
          year: getYear(),
          section: getSection(),
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
      if (!validateConfig()) return;
      const topic = $('#quiz-topic').value.trim();
      if (!topic) { showToast('Enter a quiz topic.', 'error'); return; }

      const resultEl = $('#result-quiz');
      showSkeleton(resultEl);
      setLoading(btnQuiz, true);

      try {
        const data = await apiPost('/generate/quiz', {
          year: getYear(),
          section: getSection(),
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
    // Feed sub-tab switching
    const feedTabs = $$('.feed-tab');
    const feedMy = $('#feed-my');
    const feedPublic = $('#feed-public');

    feedTabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        feedTabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        const target = tab.dataset.feed;
        if (target === 'my') {
          feedMy.hidden = false;
          feedPublic.hidden = true;
        } else {
          feedMy.hidden = true;
          feedPublic.hidden = false;
        }
      });
    });

    // Feed refresh
    const btnFeed = $('#btn-feed');
    btnFeed.addEventListener('click', async () => {
      const skeleton = `
        <div class="skeleton skeleton-lg"></div>
        <div class="skeleton skeleton-md"></div>
        <div class="skeleton skeleton-md"></div>
      `;
      feedMy.innerHTML = skeleton;
      feedPublic.innerHTML = skeleton;

      try {
        const data = await apiGet('/feed', {
          year: getYear(),
          subject: getSubject(),
          limit: 50,
        });

        renderFeedItems(feedMy, data.my_items || [], true);
        renderFeedItems(feedPublic, data.public_items || [], false);

      } catch (err) {
        feedMy.innerHTML = `<p style="color:var(--error)">Error: ${escapeHtml(err.message)}</p>`;
        feedPublic.innerHTML = `<p style="color:var(--error)">Error: ${escapeHtml(err.message)}</p>`;
        showToast(err.message, 'error');
      }
    });

    function renderFeedItems(container, items, isPersonal) {
      if (items.length === 0) {
        const label = isPersonal ? 'your personal' : 'the public';
        container.innerHTML = `
          <div class="feed-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <p>No content in ${label} feed yet.<br/>Generate some content to see it here!</p>
          </div>`;
        return;
      }

      container.innerHTML = '';
      for (const item of items) {
        const typeClass = `feed-type-${item.content_type}`;
        const date = item.created_at ? new Date(item.created_at).toLocaleString() : '';
        const userName = item.user_display_name || 'Anonymous';
        const initial = getInitial(userName);

        const feedEl = document.createElement('div');
        feedEl.className = 'feed-item';
        feedEl.innerHTML = `
          <div class="feed-header">
            <div class="feed-user-avatar">${initial}</div>
            <span class="feed-user-name">${escapeHtml(userName)}</span>
            <span class="feed-type-badge ${typeClass}">${escapeHtml(item.content_type)}</span>
            <span class="feed-meta">${escapeHtml(item.subject)} · ${escapeHtml(item.section || '')} · ${date}</span>
          </div>
          ${item.query_text ? `<p class="feed-query">"${escapeHtml(item.query_text)}"</p>` : ''}
          <div class="feed-content" id="feed-content-${item.id}">
            ${renderMarkdown(item.content)}
          </div>
          <button class="feed-expand" data-target="feed-content-${item.id}">Show more ▾</button>
          ${renderSources(item.sources)}
        `;
        container.appendChild(feedEl);
      }

      // Expand/collapse
      container.querySelectorAll('.feed-expand').forEach((btn) => {
        btn.addEventListener('click', () => {
          const target = document.getElementById(btn.dataset.target);
          if (target) {
            const isExpanded = target.classList.toggle('expanded');
            btn.textContent = isExpanded ? 'Show less ▴' : 'Show more ▾';
          }
        });
      });
    }

    // ---- Auto-load feed on tab switch ----
    const feedTab = $('#tab-feed');
    if (feedTab) {
      feedTab.addEventListener('click', () => {
        setTimeout(() => btnFeed.click(), 100);
      });
    }

  }); // end DOMContentLoaded
})();
