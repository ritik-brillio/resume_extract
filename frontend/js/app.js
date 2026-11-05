/**
 * TalentMatch Pro - Enterprise ATS Candidate Evaluator
 * Production-Grade Client Application
 */

(function() {
  'use strict';

  // ── Global State ───────────────────────────────────────────────────────────
  const state = {
    files: [],
    mustHaveTags: ['Python', 'FastAPI', 'Pytest', 'SQL'],
    goodHaveTags: ['Docker', 'AWS', 'CI/CD'],
    reportData: null,
    reportMarkdown: '',
    customPresets: {},
    searchTerm: '',
    progressInterval: null,
    timerInterval: null,
    elapsedSeconds: 0,
  };

  // ── DOM Element References ────────────────────────────────────────────────
  const elements = {
    // Header
    themeToggleBtn: document.getElementById('themeToggleBtn'),
    archModalBtn: document.getElementById('archModalBtn'),
    archModal: document.getElementById('archModal'),
    closeArchModal: document.getElementById('closeArchModal'),

    // Candidate Pool
    dropzone: document.getElementById('dropzone'),
    fileInput: document.getElementById('fileInput'),
    filePoolContainer: document.getElementById('filePoolContainer'),
    filePoolList: document.getElementById('filePoolList'),
    poolCountLabel: document.getElementById('poolCountLabel'),
    clearPoolBtn: document.getElementById('clearPoolBtn'),

    // Job Profile & Matrix
    rolePresetSelect: document.getElementById('rolePresetSelect'),
    addRoleBtn: document.getElementById('addRoleBtn'),
    mustHaveBox: document.getElementById('mustHaveBox'),
    mustHaveInput: document.getElementById('mustHaveInput'),
    goodHaveBox: document.getElementById('goodHaveBox'),
    goodHaveInput: document.getElementById('goodHaveInput'),
    jdTextarea: document.getElementById('jdTextarea'),
    jdCharCount: document.getElementById('jdCharCount'),

    // Actions
    evaluateBtn: document.getElementById('evaluateBtn'),
    evaluateBtnText: document.getElementById('evaluateBtnText'),
    evaluateSpinner: document.getElementById('evaluateSpinner'),
    resetBtn: document.getElementById('resetBtn'),
    errorBanner: document.getElementById('errorBanner'),

    // Progress Card & Loading Bar
    progressCard: document.getElementById('progressCard'),
    progressStageTitle: document.getElementById('progressStageTitle'),
    progressBarFill: document.getElementById('progressBarFill'),
    progressPctBadge: document.getElementById('progressPctBadge'),
    progressTimerBadge: document.getElementById('progressTimerBadge'),

    // Results Suite
    resultsSuite: document.getElementById('resultsSuite'),
    kpiTotalCandidates: document.getElementById('kpiTotalCandidates'),
    kpiTopScore: document.getElementById('kpiTopScore'),
    kpiAvgScore: document.getElementById('kpiAvgScore'),
    kpiSkillsMet: document.getElementById('kpiSkillsMet'),
    reportMarkdownBody: document.getElementById('reportMarkdownBody'),

    // Export buttons
    exportCsvBtn: document.getElementById('exportCsvBtn'),
    copyMarkdownBtn: document.getElementById('copyMarkdownBtn'),
    downloadMdBtn: document.getElementById('downloadMdBtn'),

    // Add Custom Role Modal
    customRoleModal: document.getElementById('customRoleModal'),
    closeCustomRoleModal: document.getElementById('closeCustomRoleModal'),
    cancelCustomRoleBtn: document.getElementById('cancelCustomRoleBtn'),
    saveCustomRoleBtn: document.getElementById('saveCustomRoleBtn'),
    customRoleTitleInput: document.getElementById('customRoleTitleInput'),
    customRoleMustHaveInput: document.getElementById('customRoleMustHaveInput'),
    customRoleGoodHaveInput: document.getElementById('customRoleGoodHaveInput'),
    customRoleJdInput: document.getElementById('customRoleJdInput'),

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage'),
  };

  // ── Role Presets Catalog ───────────────────────────────────────────────────
  const ROLE_PRESETS = {
    'senior-python': {
      title: 'Senior Python / Backend Engineer',
      mustHave: ['Python', 'FastAPI', 'PostgreSQL', 'Pytest', 'REST APIs'],
      goodHave: ['Docker', 'AWS', 'Redis', 'CI/CD', 'Kubernetes'],
      jd: `Job Title: Senior Python / Backend Engineer
Required Experience: 3+ years of professional backend development.

Key Responsibilities:
- Design, build, and maintain high-performance asynchronous microservices using Python and FastAPI.
- Architect robust database schemas and write optimized queries for PostgreSQL.
- Implement comprehensive unit and integration test suites using Pytest.
- Collaborate with frontend and infrastructure engineers on API contracts and deployments.

Required Technical Skills:
- Advanced proficiency in Python 3.10+ and asynchronous programming (asyncio, FastAPI).
- Deep experience with relational databases (PostgreSQL) and SQLAlchemy.
- Solid automated testing fundamentals (Pytest, mock, fixtures).

Good to Have:
- Hands-on experience with Docker, AWS cloud services (ECS, S3), Redis caching, and CI/CD pipelines.`
    },
    'data-engineer': {
      title: 'Data Engineer',
      mustHave: ['Python', 'SQL', 'Apache Spark', 'Data Pipelines', 'ETL'],
      goodHave: ['Airflow', 'Kafka', 'Snowflake', 'AWS', 'Databricks'],
      jd: `Job Title: Data Engineer
Required Experience: 3+ years in data pipeline engineering and data architecture.

Key Responsibilities:
- Design, build, and optimize robust batch and streaming ETL/ELT data pipelines using Python, SQL, and Apache Spark.
- Architect high-throughput data ingestion pipelines and maintain relational and analytical data warehouses.
- Build automated workflow orchestration DAGs using Apache Airflow.
- Ensure data quality, integrity, and schema evolution across distributed data platforms.

Required Technical Skills:
- Advanced proficiency in Python and SQL (complex analytical queries, indexing, window functions).
- Deep experience with Apache Spark (PySpark) for distributed data processing.
- Proven hands-on track record building production ETL pipelines.

Good to Have:
- Experience with Airflow, Kafka, Snowflake, Databricks, and AWS cloud storage (S3, Redshift).`
    },
    'data-scientist': {
      title: 'Data Scientist',
      mustHave: ['Python', 'Machine Learning', 'SQL', 'Statistics', 'Scikit-Learn'],
      goodHave: ['Deep Learning', 'PyTorch', 'Pandas', 'A/B Testing', 'Feature Engineering'],
      jd: `Job Title: Data Scientist
Required Experience: 2–5 years delivering machine learning solutions and predictive models.

Key Responsibilities:
- Formulate business challenges into statistical and machine learning models.
- Perform exploratory data analysis, feature engineering, and predictive modeling using Python, Scikit-Learn, and Pandas.
- Design, deploy, and evaluate statistical hypotheses and A/B test experiments.
- Present model metrics, ROI, and insights clearly to technical and executive stakeholders.

Required Technical Skills:
- Strong programming in Python (NumPy, Pandas, Scikit-Learn).
- Solid foundation in probability, statistics, regression, classification, and model evaluation metrics.
- Proficiency in writing complex SQL queries for data extraction and feature curation.

Good to Have:
- Hands-on experience with deep learning frameworks (PyTorch or TensorFlow), A/B testing methodologies, and ML deployment.`
    },
    'qa-automation': {
      title: 'AI QA & Test Automation Engineer (SDET)',
      mustHave: ['Python', 'Selenium', 'Pytest', 'API Testing', 'Test Automation'],
      goodHave: ['Playwright', 'Docker', 'CI/CD', 'Postman', 'LLM Evaluation'],
      jd: `Job Title: AI QA Automation Engineer / SDET
Experience: 2–5 Years in software quality engineering and test automation.

Core Responsibilities:
- Design, implement, and maintain scalable end-to-end automation frameworks using Python, Selenium, and Pytest.
- Conduct comprehensive API test automation and integration testing.
- Integrate automated regression suites into CI/CD build pipelines.
- Verify software quality and evaluate AI/LLM system outputs.

Technical Requirements:
- Hands-on Python test automation with Pytest and Selenium WebDriver.
- Strong API testing proficiency using Postman or Python Requests.
- CI/CD pipeline integration and automated reporting.`
    },
    'frontend-engineer': {
      title: 'Senior Frontend Engineer (React/TypeScript)',
      mustHave: ['React', 'TypeScript', 'HTML5', 'CSS3', 'State Management'],
      goodHave: ['Next.js', 'Tailwind CSS', 'Vite', 'Jest', 'Playwright'],
      jd: `Job Title: Senior Frontend Engineer
Required Experience: 3+ years building responsive web applications.

Responsibilities:
- Build modular, accessible, and performant web interfaces in React and TypeScript.
- Manage client state effectively using modern patterns (Zustand, Redux Toolkit, React Query).
- Translate Figma designs into pixel-perfect, accessible UI components.

Technical Skills:
- Deep expertise in React, TypeScript, and modern JavaScript (ES6+).
- Strong CSS proficiency (Tailwind CSS, CSS Modules) and responsive web design.
- Automated testing with Jest, Vitest, or React Testing Library.`
    },
    'fullstack-engineer': {
      title: 'Full Stack Engineer (Node/React/Cloud)',
      mustHave: ['React', 'Node.js', 'TypeScript', 'SQL', 'REST APIs'],
      goodHave: ['Next.js', 'Docker', 'GraphQL', 'AWS', 'MongoDB'],
      jd: `Job Title: Full Stack Software Engineer
Experience: 3+ years across frontend and backend stacks.

Responsibilities:
- Deliver end-to-end features across responsive React user interfaces and Node.js microservices.
- Design clean RESTful and GraphQL APIs for web and mobile clients.
- Optimize database performance and implement secure authentication protocols.

Core Skills:
- Proficiency in React, Node.js, and TypeScript.
- Strong SQL database design and query optimization skills.
- Experience with Git, Docker, and cloud deployments.`
    },
    'devops-engineer': {
      title: 'DevOps / Cloud Platform Engineer',
      mustHave: ['Docker', 'Kubernetes', 'Terraform', 'AWS', 'CI/CD'],
      goodHave: ['Prometheus', 'Grafana', 'Python', 'Linux', 'Helm'],
      jd: `Job Title: DevOps Platform Engineer
Experience: 3–6 years managing cloud infrastructure.

Responsibilities:
- Provision, monitor, and scale infrastructure on AWS using Terraform.
- Maintain production Kubernetes clusters, Helm charts, and container orchestration.
- Build reliable CI/CD release pipelines with GitHub Actions.

Technical Skills:
- Strong containerization expertise (Docker, Kubernetes).
- Infrastructure as Code (Terraform) and AWS cloud services.
- Linux administration and automated scripting.`
    },
    'aiml-engineer': {
      title: 'AI / Machine Learning Engineer',
      mustHave: ['Python', 'PyTorch', 'LLMs', 'NLP', 'RAG'],
      goodHave: ['LangChain', 'Vector Databases', 'Transformers', 'Docker', 'FastAPI'],
      jd: `Job Title: AI / Machine Learning Engineer
Experience: 2+ years deploying machine learning and LLM applications.

Responsibilities:
- Design, evaluate, and deploy retrieval-augmented generation (RAG) pipelines and LLM applications.
- Fine-tune embedding and NLP models using PyTorch and Hugging Face Transformers.
- Build low-latency inference services using FastAPI and vector search engines.

Skills:
- Strong Python programming and PyTorch or TensorFlow modeling.
- Hands-on experience with LLMs, prompt engineering, and vector databases.`
    }
  };

  // ── Custom Presets in LocalStorage ─────────────────────────────────────────
  function loadCustomPresets() {
    try {
      const saved = localStorage.getItem('tm_custom_presets');
      if (saved) {
        state.customPresets = JSON.parse(saved);
      }
    } catch(e) {
      state.customPresets = {};
    }
    populatePresetDropdown();
  }

  function saveCustomPresetsToStorage() {
    try {
      localStorage.setItem('tm_custom_presets', JSON.stringify(state.customPresets));
    } catch(e) {}
  }

  function populatePresetDropdown() {
    if (!elements.rolePresetSelect) return;
    const currentVal = elements.rolePresetSelect.value;

    // Reset dropdown to standard presets
    elements.rolePresetSelect.innerHTML = `
      <option value="">-- Choose Role Preset --</option>
      <optgroup label="Standard Roles">
        <option value="senior-python">Senior Python / Backend</option>
        <option value="data-engineer">Data Engineer</option>
        <option value="data-scientist">Data Scientist</option>
        <option value="qa-automation">AI QA &amp; SDET Automation</option>
        <option value="frontend-engineer">Frontend Engineer (React/TS)</option>
        <option value="fullstack-engineer">Full Stack Engineer</option>
        <option value="devops-engineer">DevOps &amp; Cloud Platform</option>
        <option value="aiml-engineer">AI / Machine Learning Engineer</option>
      </optgroup>
    `;

    // Add Custom Roles optgroup if any exist
    const customKeys = Object.keys(state.customPresets);
    if (customKeys.length > 0) {
      const optgroup = document.createElement('optgroup');
      optgroup.label = 'Custom Roles';
      customKeys.forEach(key => {
        const opt = document.createElement('option');
        opt.value = `custom_${key}`;
        opt.textContent = state.customPresets[key].title;
        optgroup.appendChild(opt);
      });
      elements.rolePresetSelect.appendChild(optgroup);
    }

    if (currentVal) {
      elements.rolePresetSelect.value = currentVal;
    }
  }

  function openAddRoleModal() {
    if (!elements.customRoleModal) return;
    if (elements.customRoleTitleInput) elements.customRoleTitleInput.value = '';
    if (elements.customRoleMustHaveInput) elements.customRoleMustHaveInput.value = '';
    if (elements.customRoleGoodHaveInput) elements.customRoleGoodHaveInput.value = '';
    if (elements.customRoleJdInput) elements.customRoleJdInput.value = '';
    elements.customRoleModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    if (elements.customRoleTitleInput) elements.customRoleTitleInput.focus();
  }

  function closeAddRoleModal() {
    if (!elements.customRoleModal) return;
    elements.customRoleModal.classList.add('hidden');
    document.body.style.overflow = '';
  }

  function saveCustomRole() {
    const title = elements.customRoleTitleInput ? elements.customRoleTitleInput.value.trim() : '';
    const mustStr = elements.customRoleMustHaveInput ? elements.customRoleMustHaveInput.value.trim() : '';
    const goodStr = elements.customRoleGoodHaveInput ? elements.customRoleGoodHaveInput.value.trim() : '';
    const jd = elements.customRoleJdInput ? elements.customRoleJdInput.value.trim() : '';

    if (!title) {
      alert('Please enter a role title (e.g. "Data Platform Architect").');
      return;
    }
    if (!mustStr) {
      alert('Please enter at least one Must-Have skill (comma-separated).');
      return;
    }

    const key = title.toLowerCase().replace(/[^a-z0-9]+/g, '_');
    const mustHave = mustStr.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
    const goodHave = goodStr.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);

    state.customPresets[key] = {
      title: title,
      mustHave: mustHave,
      goodHave: goodHave,
      jd: jd || `Role Title: ${title}\nRequired Skills: ${mustHave.join(', ')}\nGood to Have: ${goodHave.join(', ')}`
    };

    saveCustomPresetsToStorage();
    populatePresetDropdown();
    closeAddRoleModal();

    // Select the new custom preset
    if (elements.rolePresetSelect) {
      elements.rolePresetSelect.value = `custom_${key}`;
      applyRolePreset(`custom_${key}`);
    }
    showToast(`Saved and applied "${title}" preset!`);
  }

  // ── Theme Management ───────────────────────────────────────────────────────
  function initTheme() {
    let savedTheme = 'dark';
    try {
      savedTheme = localStorage.getItem('tm_theme') || 
        (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    } catch(e) {}
    setTheme(savedTheme);
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('tm_theme', theme);
    } catch(e) {}
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
  }

  // ── Toast Utility ──────────────────────────────────────────────────────────
  let toastTimer = null;
  function showToast(message) {
    if (!elements.toast || !elements.toastMessage) return;
    elements.toastMessage.textContent = message;
    elements.toast.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      elements.toast.classList.add('hidden');
    }, 2800);
  }

  // ── Skill Tag Chip Management ──────────────────────────────────────────────
  function renderSkillTags(container, tags, type) {
    if (!container) return;
    const input = container.querySelector('.tag-text-input');
    container.querySelectorAll('.skill-tag-chip').forEach(el => el.remove());

    tags.forEach((tag, idx) => {
      const chip = document.createElement('span');
      chip.className = `skill-tag-chip ${type === 'must' ? 'must-have-chip' : 'good-have-chip'}`;
      chip.innerHTML = `
        <span>${escapeHtml(tag)}</span>
        <span class="chip-close" data-type="${type}" data-idx="${idx}" title="Remove skill">✕</span>
      `;
      container.insertBefore(chip, input);
    });
  }

  function addSkillTag(type, value) {
    const cleaned = value.trim().replace(/^[,;\s]+|[,;\s]+$/g, '');
    if (!cleaned) return;

    const parts = cleaned.split(/[,;\n]+/).map(p => p.trim()).filter(Boolean);
    const targetArr = type === 'must' ? state.mustHaveTags : state.goodHaveTags;

    parts.forEach(part => {
      const exists = targetArr.some(t => t.toLowerCase() === part.toLowerCase());
      if (!exists) {
        targetArr.push(part);
      }
    });

    if (type === 'must') {
      renderSkillTags(elements.mustHaveBox, state.mustHaveTags, 'must');
      if (elements.mustHaveInput) elements.mustHaveInput.value = '';
    } else {
      renderSkillTags(elements.goodHaveBox, state.goodHaveTags, 'good');
      if (elements.goodHaveInput) elements.goodHaveInput.value = '';
    }
    updateEvaluateButton();
  }

  function removeSkillTag(type, idx) {
    if (type === 'must') {
      state.mustHaveTags.splice(idx, 1);
      renderSkillTags(elements.mustHaveBox, state.mustHaveTags, 'must');
    } else {
      state.goodHaveTags.splice(idx, 1);
      renderSkillTags(elements.goodHaveBox, state.goodHaveTags, 'good');
    }
    updateEvaluateButton();
  }

  // ── File Management (Candidate Pool) ───────────────────────────────────────
  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function getFileExtension(filename) {
    const parts = (filename || '').split('.');
    return parts.length > 1 ? parts.pop().toUpperCase() : 'DOC';
  }

  function renderFilePool() {
    if (!elements.filePoolList) return;
    elements.filePoolList.innerHTML = '';

    const count = state.files.length;
    if (elements.poolCountLabel) {
      elements.poolCountLabel.textContent = `${count} Candidate Resume${count === 1 ? '' : 's'} Selected`;
    }

    if (elements.filePoolContainer) {
      elements.filePoolContainer.classList.toggle('hidden', count === 0);
    }

    state.files.forEach((file, idx) => {
      const row = document.createElement('div');
      row.className = 'file-pool-row';
      row.innerHTML = `
        <div class="file-row-meta">
          <span class="file-type-badge">${getFileExtension(file.name)}</span>
          <span class="file-name-text" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
          <span class="file-size-text">(${formatBytes(file.size)})</span>
        </div>
        <button class="file-remove-btn" data-idx="${idx}" title="Remove candidate">✕</button>
      `;
      elements.filePoolList.appendChild(row);
    });

    updateEvaluateButton();
  }

  function addFiles(newFiles) {
    if (!newFiles || !newFiles.length) return;
    const existing = new Set(state.files.map(f => f.name.toLowerCase()));
    Array.from(newFiles).forEach(file => {
      if (!existing.has(file.name.toLowerCase())) {
        state.files.push(file);
        existing.add(file.name.toLowerCase());
      }
    });
    if (elements.fileInput) elements.fileInput.value = '';
    renderFilePool();
  }

  function removeFile(idx) {
    if (idx >= 0 && idx < state.files.length) {
      state.files.splice(idx, 1);
    }
    renderFilePool();
  }

  function clearPool() {
    state.files = [];
    if (elements.fileInput) elements.fileInput.value = '';
    renderFilePool();
  }

  // ── Role Preset Handlers ───────────────────────────────────────────────────
  function applyRolePreset(key) {
    let preset = ROLE_PRESETS[key];
    if (!preset && key.startsWith('custom_')) {
      const customKey = key.replace('custom_', '');
      preset = state.customPresets[customKey];
    }
    if (!preset) return;

    state.mustHaveTags = [...preset.mustHave];
    state.goodHaveTags = [...preset.goodHave];
    renderSkillTags(elements.mustHaveBox, state.mustHaveTags, 'must');
    renderSkillTags(elements.goodHaveBox, state.goodHaveTags, 'good');

    if (elements.jdTextarea) {
      elements.jdTextarea.value = preset.jd;
      updateCharCount();
    }
    showToast(`Loaded ${preset.title} profile`);
    updateEvaluateButton();
  }

  function updateCharCount() {
    if (!elements.jdTextarea || !elements.jdCharCount) return;
    const len = elements.jdTextarea.value.length;
    elements.jdCharCount.textContent = `${len.toLocaleString()} characters`;
  }

  function updateEvaluateButton() {
    if (!elements.evaluateBtn || !elements.evaluateBtnText) return;
    const count = state.files.length;
    if (count > 0) {
      elements.evaluateBtnText.textContent = `⚡ Evaluate ${count} Candidate${count > 1 ? 's' : ''}`;
    } else {
      elements.evaluateBtnText.textContent = '⚡ Run Candidate Evaluation & Match';
    }
  }

  // ── Progress Bar & Stage Simulation ───────────────────────────────────────
  const PROGRESS_STAGES = [
    { threshold: 15, title: 'Step 1/4: Ingesting & normalizing candidate resumes...' },
    { threshold: 40, title: 'Step 2/4: Chunking passages & parsing priority requirements...' },
    { threshold: 70, title: 'Step 3/4: Generating dense semantic embeddings (all-MiniLM-L6-v2) & BM25 indices...' },
    { threshold: 92, title: 'Step 4/4: Calibrating ATS sigmoidal curve & computing candidate rankings...' },
  ];

  function startProgressTracking() {
    if (elements.progressCard) {
      elements.progressCard.classList.remove('hidden');
    }
    if (elements.resultsSuite) {
      elements.resultsSuite.classList.add('hidden');
    }
    if (elements.progressBarFill) {
      elements.progressBarFill.style.width = '5%';
    }
    if (elements.progressPctBadge) {
      elements.progressPctBadge.textContent = '5%';
    }
    if (elements.progressStageTitle) {
      elements.progressStageTitle.textContent = PROGRESS_STAGES[0].title;
    }

    state.elapsedSeconds = 0;
    if (elements.progressTimerBadge) {
      elements.progressTimerBadge.textContent = '⏱️ 0s';
    }

    clearInterval(state.timerInterval);
    state.timerInterval = setInterval(() => {
      state.elapsedSeconds += 1;
      if (elements.progressTimerBadge) {
        elements.progressTimerBadge.textContent = `⏱️ ${state.elapsedSeconds}s`;
      }
    }, 1000);

    let currentPct = 5;
    clearInterval(state.progressInterval);
    state.progressInterval = setInterval(() => {
      if (currentPct < 90) {
        // Increment smoothly
        const step = currentPct < 40 ? 4 : (currentPct < 70 ? 2.5 : 1.2);
        currentPct = Math.min(92, currentPct + step);
        if (elements.progressBarFill) {
          elements.progressBarFill.style.width = `${currentPct.toFixed(0)}%`;
        }
        if (elements.progressPctBadge) {
          elements.progressPctBadge.textContent = `${currentPct.toFixed(0)}%`;
        }

        // Update stage label
        const stage = PROGRESS_STAGES.slice().reverse().find(s => currentPct >= s.threshold);
        if (stage && elements.progressStageTitle) {
          elements.progressStageTitle.textContent = stage.title;
        }
      }
    }, 350);
  }

  function finishProgressTracking(onComplete) {
    clearInterval(state.progressInterval);
    clearInterval(state.timerInterval);

    if (elements.progressBarFill) {
      elements.progressBarFill.style.width = '100%';
    }
    if (elements.progressPctBadge) {
      elements.progressPctBadge.textContent = '100%';
    }
    if (elements.progressStageTitle) {
      elements.progressStageTitle.textContent = '✨ Complete: Rendering executive report & scorecard!';
    }

    setTimeout(() => {
      if (elements.progressCard) {
        elements.progressCard.classList.add('hidden');
      }
      if (onComplete) onComplete();
    }, 450);
  }

  function stopProgressOnError() {
    clearInterval(state.progressInterval);
    clearInterval(state.timerInterval);
    if (elements.progressCard) {
      elements.progressCard.classList.add('hidden');
    }
  }

  // ── Evaluation Execution ───────────────────────────────────────────────────
  async function runEvaluation(e) {
    if (e && e.preventDefault) e.preventDefault();

    if (elements.errorBanner) elements.errorBanner.classList.add('hidden');

    if (!state.files.length) {
      showError('Please upload at least one candidate resume (.pdf, .docx, or .txt) in Step 1.');
      if (elements.dropzone) elements.dropzone.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    const jdText = elements.jdTextarea ? elements.jdTextarea.value.trim() : '';
    const mustHaveStr = state.mustHaveTags.join(', ');
    const goodHaveStr = state.goodHaveTags.join(', ');

    if (!jdText && !mustHaveStr) {
      showError('Please paste a Job Description in Step 2 or specify Must-Have Skills to evaluate against.');
      if (elements.jdTextarea) elements.jdTextarea.focus();
      return;
    }

    // Set UI loading state
    if (elements.evaluateBtn) elements.evaluateBtn.disabled = true;
    if (elements.evaluateSpinner) elements.evaluateSpinner.classList.remove('hidden');
    if (elements.evaluateBtnText) elements.evaluateBtnText.textContent = 'Analyzing Resumes...';

    // Start animated progress tracking bar
    startProgressTracking();

    const formData = new FormData();
    state.files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('jd_text', jdText || 'Software Engineering Role');
    formData.append('must_have_skills', mustHaveStr);
    formData.append('good_to_have_skills', goodHaveStr);

    try {
      const res = await fetch('/api/analyse', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Server returned error status ${res.status}`);
      }

      state.reportData = data.report || null;
      state.reportMarkdown = data.markdown || '';

      finishProgressTracking(() => {
        renderEvaluationResults();
        showToast('Candidate evaluation complete!');

        if (elements.resultsSuite) {
          elements.resultsSuite.classList.remove('hidden');
          elements.resultsSuite.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });

    } catch (err) {
      stopProgressOnError();
      showError(`Analysis failed: ${err.message}. Please verify the server is running.`);
    } finally {
      if (elements.evaluateBtn) elements.evaluateBtn.disabled = false;
      if (elements.evaluateSpinner) elements.evaluateSpinner.classList.add('hidden');
      updateEvaluateButton();
    }
  }

  function showError(msg) {
    if (!elements.errorBanner) return;
    elements.errorBanner.textContent = `⚠️ ${msg}`;
    elements.errorBanner.classList.remove('hidden');
  }

  // ── Results Rendering ──────────────────────────────────────────────────────
  function renderEvaluationResults() {
    if (!state.reportMarkdown) {
      showError('No report output received from analysis engine.');
      return;
    }

    // 1. Update KPI Analytics if reportData exists
    if (state.reportData && state.reportData.candidates) {
      const candidates = state.reportData.candidates;
      if (elements.kpiTotalCandidates) {
        elements.kpiTotalCandidates.textContent = candidates.length;
      }
      if (elements.kpiTopScore) {
        const top = Math.max(...candidates.map(c => c.overall_score), 0);
        elements.kpiTopScore.textContent = `${top.toFixed(1)}%`;
      }
      if (elements.kpiAvgScore) {
        const avg = candidates.length 
          ? candidates.reduce((acc, c) => acc + c.overall_score, 0) / candidates.length
          : 0;
        elements.kpiAvgScore.textContent = `${avg.toFixed(1)}%`;
      }
      if (elements.kpiSkillsMet) {
        elements.kpiSkillsMet.textContent = `${state.reportData.requirement_count} Requirements`;
      }
    } else {
      if (elements.kpiTotalCandidates) elements.kpiTotalCandidates.textContent = state.files.length;
      if (elements.kpiTopScore) elements.kpiTopScore.textContent = 'Active';
      if (elements.kpiAvgScore) elements.kpiAvgScore.textContent = 'Calculated';
      if (elements.kpiSkillsMet) elements.kpiSkillsMet.textContent = `${state.mustHaveTags.length + state.goodHaveTags.length} Skills`;
    }

    // 2. Render the complete Executive Markdown Report directly in UI
    if (elements.reportMarkdownBody) {
      let rawHtml = '';
      if (window.marked) {
        rawHtml = marked.parse(state.reportMarkdown || '');
      } else {
        rawHtml = `<pre>${escapeHtml(state.reportMarkdown)}</pre>`;
      }

      // Wrap all <table> with smooth horizontal scroll wrappers
      rawHtml = rawHtml
        .replace(/<table>/g, '<div class="table-scroll-wrapper"><table>')
        .replace(/<\/table>/g, '</table></div>');

      elements.reportMarkdownBody.innerHTML = rawHtml;
    }
  }

  // ── Export Functions ───────────────────────────────────────────────────────
  function exportCsv() {
    if (!state.reportData || !state.reportData.candidates) {
      showToast('No candidate data available to export.');
      return;
    }

    const headers = ['Rank', 'Candidate', 'Must_Have_Skills_Percent', 'Good_To_Have_Skills_Percent', 'Total_Experience_Years', 'Overall_ATS_Score_Percent', 'Status'];
    const rows = state.reportData.candidates.map(c => [
      c.rank,
      `"${c.source_filename.replace(/"/g, '""')}"`,
      `${c.must_have_score.toFixed(1)}%`,
      c.good_to_have_score > 0 ? `${c.good_to_have_score.toFixed(1)}%` : 'N/A',
      c.total_experience_years !== null ? `${c.total_experience_years.toFixed(1)} Years` : 'N/A',
      `${c.overall_score.toFixed(1)}%`,
      c.overall_score >= 70 ? 'Strong Match' : (c.overall_score >= 45 ? 'Moderate Match' : 'Low Match')
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `candidate_evaluation_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Exported CSV scorecard!');
  }

  function copyMarkdown() {
    if (!state.reportMarkdown) {
      showToast('No report available to copy.');
      return;
    }
    navigator.clipboard.writeText(state.reportMarkdown).then(() => {
      showToast('Copied Markdown report to clipboard!');
    }).catch(err => {
      showToast('Failed to copy: ' + err);
    });
  }

  function downloadMarkdown() {
    if (!state.reportMarkdown) {
      showToast('No report available to download.');
      return;
    }
    const blob = new Blob([state.reportMarkdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'scoring_report.md';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast('Downloaded scoring_report.md!');
  }

  // ── Reset Workspace ────────────────────────────────────────────────────────
  function resetWorkspace() {
    clearPool();
    state.mustHaveTags = ['Python', 'FastAPI', 'Pytest', 'SQL'];
    state.goodHaveTags = ['Docker', 'AWS', 'CI/CD'];
    renderSkillTags(elements.mustHaveBox, state.mustHaveTags, 'must');
    renderSkillTags(elements.goodHaveBox, state.goodHaveTags, 'good');

    if (elements.jdTextarea) elements.jdTextarea.value = '';
    updateCharCount();

    if (elements.rolePresetSelect) elements.rolePresetSelect.value = '';
    if (elements.resultsSuite) elements.resultsSuite.classList.add('hidden');
    if (elements.progressCard) elements.progressCard.classList.add('hidden');
    if (elements.errorBanner) elements.errorBanner.classList.add('hidden');

    state.reportData = null;
    state.reportMarkdown = '';
    updateEvaluateButton();
    showToast('Workspace reset to defaults');
  }

  // ── Architecture Modal ─────────────────────────────────────────────────────
  function openArchModal() {
    if (elements.archModal) {
      elements.archModal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeArchModal() {
    if (elements.archModal) {
      elements.archModal.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  function switchArchTab(tabId) {
    document.querySelectorAll('.modal-tabs .tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.modal-body .tab-content').forEach(c => {
      c.classList.toggle('active', c.id === tabId);
    });
  }

  // ── Helper Utilities ───────────────────────────────────────────────────────
  function escapeHtml(str) {
    return (str || '').replace(/[&<>"']/g, function(m) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
    });
  }

  // ── Event Listeners Binding ────────────────────────────────────────────────
  function bindEvents() {
    // Theme toggle
    if (elements.themeToggleBtn) {
      elements.themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Modal Architecture
    if (elements.archModalBtn) {
      elements.archModalBtn.addEventListener('click', openArchModal);
    }
    if (elements.closeArchModal) {
      elements.closeArchModal.addEventListener('click', closeArchModal);
    }
    if (elements.archModal) {
      elements.archModal.addEventListener('click', (e) => {
        if (e.target === elements.archModal) closeArchModal();
      });
    }

    document.querySelectorAll('.modal-tabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => switchArchTab(btn.dataset.tab));
    });

    // Custom Role Modal
    if (elements.addRoleBtn) {
      elements.addRoleBtn.addEventListener('click', openAddRoleModal);
    }
    if (elements.closeCustomRoleModal) {
      elements.closeCustomRoleModal.addEventListener('click', closeAddRoleModal);
    }
    if (elements.cancelCustomRoleBtn) {
      elements.cancelCustomRoleBtn.addEventListener('click', closeAddRoleModal);
    }
    if (elements.saveCustomRoleBtn) {
      elements.saveCustomRoleBtn.addEventListener('click', saveCustomRole);
    }
    if (elements.customRoleModal) {
      elements.customRoleModal.addEventListener('click', (e) => {
        if (e.target === elements.customRoleModal) closeAddRoleModal();
      });
    }

    // Dropzone
    if (elements.dropzone) {
      elements.dropzone.addEventListener('click', () => {
        if (elements.fileInput) elements.fileInput.click();
      });
      elements.dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropzone.classList.add('drag-active');
      });
      elements.dropzone.addEventListener('dragleave', () => {
        elements.dropzone.classList.remove('drag-active');
      });
      elements.dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.dropzone.classList.remove('drag-active');
        if (e.dataTransfer && e.dataTransfer.files) {
          addFiles(e.dataTransfer.files);
        }
      });
    }

    if (elements.fileInput) {
      elements.fileInput.addEventListener('change', (e) => {
        if (e.target.files) addFiles(e.target.files);
      });
    }

    if (elements.filePoolList) {
      elements.filePoolList.addEventListener('click', (e) => {
        const btn = e.target.closest('.file-remove-btn');
        if (btn) {
          removeFile(Number(btn.dataset.idx));
        }
      });
    }

    if (elements.clearPoolBtn) {
      elements.clearPoolBtn.addEventListener('click', clearPool);
    }

    // Role Presets Dropdown
    if (elements.rolePresetSelect) {
      elements.rolePresetSelect.addEventListener('change', (e) => {
        if (e.target.value) applyRolePreset(e.target.value);
      });
    }

    // Skill Tag Inputs
    if (elements.mustHaveInput) {
      elements.mustHaveInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
          e.preventDefault();
          addSkillTag('must', elements.mustHaveInput.value);
        }
      });
    }

    if (elements.goodHaveInput) {
      elements.goodHaveInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
          e.preventDefault();
          addSkillTag('good', elements.goodHaveInput.value);
        }
      });
    }

    // Remove chip clicks
    if (elements.mustHaveBox) {
      elements.mustHaveBox.addEventListener('click', (e) => {
        const close = e.target.closest('.chip-close');
        if (close) {
          removeSkillTag(close.dataset.type, Number(close.dataset.idx));
        } else if (elements.mustHaveInput) {
          elements.mustHaveInput.focus();
        }
      });
    }

    if (elements.goodHaveBox) {
      elements.goodHaveBox.addEventListener('click', (e) => {
        const close = e.target.closest('.chip-close');
        if (close) {
          removeSkillTag(close.dataset.type, Number(close.dataset.idx));
        } else if (elements.goodHaveInput) {
          elements.goodHaveInput.focus();
        }
      });
    }

    // JD textarea
    if (elements.jdTextarea) {
      elements.jdTextarea.addEventListener('input', updateCharCount);
    }

    // Action buttons
    if (elements.evaluateBtn) {
      elements.evaluateBtn.addEventListener('click', runEvaluation);
    }
    if (elements.resetBtn) {
      elements.resetBtn.addEventListener('click', resetWorkspace);
    }

    // Export buttons
    if (elements.exportCsvBtn) {
      elements.exportCsvBtn.addEventListener('click', exportCsv);
    }
    if (elements.copyMarkdownBtn) {
      elements.copyMarkdownBtn.addEventListener('click', copyMarkdown);
    }
    if (elements.downloadMdBtn) {
      elements.downloadMdBtn.addEventListener('click', downloadMarkdown);
    }

    // Global keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runEvaluation();
      } else if (e.key === 'Escape') {
        closeAddRoleModal();
        closeArchModal();
      }
    });
  }

  // ── Initialization ────────────────────────────────────────────────────────
  function init() {
    initTheme();
    loadCustomPresets();
    renderSkillTags(elements.mustHaveBox, state.mustHaveTags, 'must');
    renderSkillTags(elements.goodHaveBox, state.goodHaveTags, 'good');
    updateCharCount();
    bindEvents();
    updateEvaluateButton();
  }

  // Run on DOM loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
