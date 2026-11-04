/* ── Theme Switcher ──────────────────────────────────────────────────────── */
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try {
    localStorage.setItem('re_theme', theme);
  } catch (e) {}

  // Re-render open diagram if modal is visible
  const modal = document.getElementById('archModal');
  if (modal && !modal.classList.contains('hidden') && typeof renderTabDiagram === 'function') {
    const activeTab = document.querySelector('.modal-tabs .tab-btn.active');
    if (activeTab && activeTab.dataset && activeTab.dataset.tab) {
      renderTabDiagram(activeTab.dataset.tab);
    }
  }
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
  applyTheme(nextTheme);
}

// Export to window for inline onclick handler
window.toggleTheme = toggleTheme;
window.applyTheme = applyTheme;

// Safe initial theme load
try {
  const savedTheme = localStorage.getItem('re_theme') || 
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  applyTheme(savedTheme);
} catch (e) {
  applyTheme('dark');
}

/* ── File Management State ───────────────────────────────────────────────── */
let selectedFiles = window.selectedFiles || [];
window.selectedFiles = selectedFiles;

const uploadZone    = document.getElementById('uploadZone');
const fileInput     = document.getElementById('fileInput');
const fileChips     = document.getElementById('fileChips');
const jdInput       = document.getElementById('jdInput');
const charCount     = document.getElementById('charCount');
const analyseBtn    = document.getElementById('analyseBtn');
const spinner       = document.getElementById('spinner');
const btnText       = analyseBtn ? analyseBtn.querySelector('.btn-text') : null;
const errorBanner   = document.getElementById('errorBanner');
const resultPanel   = document.getElementById('resultPanel');
const resultContent = document.getElementById('resultContent');

function updateButton() {
  const count = selectedFiles.length;
  if (btnText) {
    if (count > 0) {
      btnText.textContent = `Evaluate ${count} Resume${count > 1 ? 's' : ''}`;
    } else {
      btnText.textContent = 'Evaluate & Match Resumes';
    }
  }
}

function renderChips() {
  if (!fileChips) return;
  fileChips.innerHTML = '';
  selectedFiles.forEach((file, idx) => {
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.innerHTML = `
      <span>📄 ${file.name}</span>
      <span class="chip-remove" data-idx="${idx}" title="Remove file">✕</span>
    `;
    fileChips.appendChild(chip);
  });
}

function addFiles(newFiles) {
  if (!newFiles || !newFiles.length) return;
  const existingNames = new Set(selectedFiles.map(f => f.name.toLowerCase()));
  Array.from(newFiles).forEach(file => {
    if (!existingNames.has(file.name.toLowerCase())) {
      selectedFiles.push(file);
      existingNames.add(file.name.toLowerCase());
    }
  });
  if (fileInput) fileInput.value = '';
  renderChips();
  updateButton();
}

function removeFile(idx) {
  if (idx >= 0 && idx < selectedFiles.length) {
    selectedFiles.splice(idx, 1);
  }
  if (fileInput) fileInput.value = '';
  renderChips();
  updateButton();
}

// Global functions for inline HTML calls
window.triggerFileInput = function(e) {
  if (e) e.stopPropagation();
  const input = document.getElementById('fileInput');
  if (input) input.click();
};

window.handleFileChange = function(e) {
  if (e && e.target && e.target.files) {
    addFiles(e.target.files);
  }
};

window.removeFile = removeFile;

function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.classList.remove('hidden');
}

function clearError() {
  errorBanner.classList.add('hidden');
}

function setLoading(isLoading) {
  if (analyseBtn) analyseBtn.disabled = isLoading;
  if (btnText) btnText.textContent = isLoading ? 'Evaluating Resumes...' : 'Evaluate & Match Resumes';
  if (spinner) spinner.classList.toggle('hidden', !isLoading);
}

/* ── Upload Zone Events ─────────────────────────────────────────────────── */
if (uploadZone) {
  uploadZone.addEventListener('click', (e) => {
    if (e.target !== fileInput && fileInput) {
      fileInput.click();
    }
  });

  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer && e.dataTransfer.files) {
      addFiles(e.dataTransfer.files);
    }
  });
}

if (fileInput) {
  fileInput.addEventListener('change', (e) => {
    if (e.target.files) {
      addFiles(e.target.files);
    }
  });
}

if (fileChips) {
  fileChips.addEventListener('click', (e) => {
    const removeBtn = e.target.closest('.chip-remove');
    if (removeBtn) {
      const idx = Number(removeBtn.dataset.idx);
      removeFile(idx);
    }
  });
}

/* ── JD Input Event ─────────────────────────────────────────────────────── */
if (jdInput) {
  jdInput.addEventListener('input', () => {
    const count = jdInput.value.length;
    if (charCount) charCount.textContent = `${count.toLocaleString()} characters`;
    updateButton();
  });
}

/* ── Submit & Analyse ───────────────────────────────────────────────────── */
analyseBtn.addEventListener('click', async () => {
  clearError();

  if (!selectedFiles || selectedFiles.length === 0) {
    showError('Please upload at least one resume file (PDF, DOCX, or TXT) before evaluating.');
    const zone = document.getElementById('uploadZone');
    if (zone) zone.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  const jdText = jdInput ? jdInput.value.trim() : '';
  if (!jdText) {
    showError('Please paste a job description text in Step 2 to evaluate the resumes against.');
    if (jdInput) jdInput.focus();
    return;
  }

  setLoading(true);
  resultPanel.classList.add('hidden');

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append('files', f));
  formData.append('jd_text', jdInput.value.trim());

  try {
    const res = await fetch('/api/analyse', {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();

    if (!res.ok) {
      showError(`Error ${res.status}: ${data.detail || 'Analysis could not be completed.'}`);
      return;
    }

    // Render markdown report cleanly
    if (window.marked) {
      resultContent.innerHTML = marked.parse(data.markdown || '');
    } else {
      resultContent.textContent = data.markdown || '';
    }

    resultPanel.classList.remove('hidden');
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showError(`Network connection error: ${err.message}. Please verify the server is running.`);
  } finally {
    setLoading(false);
    updateButton();
  }
});

/* ── Architecture & Flow Modal ─────────────────────────────────────────── */
const archModalBtn   = document.getElementById('archModalBtn');
const archModal      = document.getElementById('archModal');
const closeArchModal = document.getElementById('closeArchModal');
const tabButtons     = document.querySelectorAll('.modal-tabs .tab-btn');
const tabContents    = document.querySelectorAll('.modal-body .tab-content');

const mermaidCache = new Map();

// Initialize mermaid library
if (window.mermaid) {
  try {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      theme: (document.documentElement.getAttribute('data-theme') || savedTheme) === 'dark' ? 'dark' : 'default',
      fontFamily: 'Plus Jakarta Sans, sans-serif'
    });
  } catch (e) {
    console.warn('Mermaid init warning:', e);
  }
}

async function renderTabDiagram(tabId) {
  const tabEl = document.getElementById(tabId);
  if (!tabEl) return;

  const mermaidPre = tabEl.querySelector('.mermaid-source') || tabEl.querySelector('.mermaid');
  const renderTarget = tabEl.querySelector('.diagram-render-target');
  if (!mermaidPre || !renderTarget) return;

  if (!mermaidCache.has(tabId)) {
    mermaidCache.set(tabId, mermaidPre.textContent.trim());
  }

  const rawCode = mermaidCache.get(tabId);
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';

  if (window.mermaid) {
    try {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        theme: currentTheme === 'dark' ? 'dark' : 'default',
        fontFamily: 'Plus Jakarta Sans, sans-serif'
      });

      const cleanId = 'diag_' + tabId.replace(/[^a-zA-Z0-9]/g, '') + '_' + Date.now();
      const { svg } = await mermaid.render(cleanId, rawCode);
      renderTarget.innerHTML = svg;
      return;
    } catch (err) {
      console.warn('Mermaid render fell back to native SVG:', err);
    }
  }
}

function openModal() {
  const modal = document.getElementById('archModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  // Render active tab diagram
  const activeTab = document.querySelector('.modal-tabs .tab-btn.active');
  if (activeTab && activeTab.dataset.tab) {
    renderTabDiagram(activeTab.dataset.tab);
  }
}

function closeModal() {
  const modal = document.getElementById('archModal');
  if (!modal) return;
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

// Bind to window for global inline calls
window.openArchModal = openModal;
window.closeArchModal = closeModal;
window.switchArchTab = function(tabId) {
  const buttons = document.querySelectorAll('.modal-tabs .tab-btn');
  const contents = document.querySelectorAll('.modal-body .tab-content');
  buttons.forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  contents.forEach(c => c.classList.toggle('active', c.id === tabId));
  renderTabDiagram(tabId);
};
window.renderActiveDiagram = function(tabId) {
  const target = tabId || (document.querySelector('.modal-tabs .tab-btn.active') || {}).dataset?.tab || 'archTab';
  renderTabDiagram(target);
};

if (archModalBtn) {
  archModalBtn.addEventListener('click', openModal);
}

if (closeArchModal) {
  closeArchModal.addEventListener('click', closeModal);
}

if (archModal) {
  archModal.addEventListener('click', (e) => {
    if (e.target === archModal) {
      closeModal();
    }
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('archModal');
    if (modal && !modal.classList.contains('hidden')) {
      closeModal();
    }
  }
});

// Tab switching event delegation
tabButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const targetTabId = btn.dataset.tab;
    if (targetTabId && window.switchArchTab) {
      window.switchArchTab(targetTabId);
    }
  });
});


