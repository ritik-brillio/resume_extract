# Resume Extractor & Scoring Engine

An AI-powered, deterministic resume extraction, candidate matching, and ATS evaluation engine. It converts multi-format resumes into clean Markdown, extracts structured sections into JSON, and scores candidates against job descriptions using a hybrid lexical (BM25) and local dense semantic embedding model (`all-MiniLM-L6-v2`).

Features an **interactive Web UI** (Light/Dark mode, drag-and-drop file upload, architecture & technical flow modal, real-time Markdown rendering, executive candidate rankings, and skill gap analysis) and a **command-line interface (CLI)**.

---

## Architecture & Project Structure

```text
resume_extract/
├── backend/                    # Core Python application modules
│   ├── __init__.py
│   ├── api.py                  # FastAPI REST server & static file router
│   ├── document_converter.py   # Document conversion to Markdown (MarkItDown)
│   ├── jd_parser.py            # JD clause splitting, category & priority detection
│   ├── matching_engine.py      # Hybrid BM25 + dense semantic scoring & ATS calibration
│   ├── resume_chunker.py       # Section passage segmentation & date metadata
│   ├── resume_extractor.py     # Section heading mapping & contact extraction
│   └── scoring_report.py       # Ranked scoring report & gap analysis generation
├── frontend/                   # Modern Web User Interface
│   ├── index.html              # Clean SPA layout with Light/Dark mode & Architecture modal
│   ├── css/style.css           # Modern CSS system (Dark/Light themes, responsive cards)
│   └── js/app.js               # Multi-upload state, API integration, and diagram rendering
├── Resume/                     # Input folder for sample resumes and JD documents
├── outputs/                    # Output directory for .md, .json, and scoring_report.md
├── tests/                      # Unit test suite
│   └── test_resume_extractor.py
├── docs/                       # Comprehensive documentation
│   ├── architecture.md         # System topology diagram, execution flow & rubric details
│   └── scoring-design.md       # Underlying scoring theory & retrieval design
├── main.py                     # Unified launcher (Auto-port Web server & CLI)
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## Key Features

- **Multi-Format Support:** Converts `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`, `.html`, and `.csv` up to 15 MB.
- **Privacy-First & Fully Local:** Powered by local Sentence Transformers (`all-MiniLM-L6-v2`) and BM25. No data is sent to external LLMs, third-party APIs, or cloud services.
- **Universal Engineering Profile Support:** Fully calibrated for all technical roles:
  - **Full Stack Developers** (Frontend + Backend + Databases + CI/CD)
  - **Frontend Engineers** (React, Next.js, Vue, Angular, TypeScript, UI/UX)
  - **Backend Engineers** (Node.js, Python, Go, Java, APIs, Microservices, SQL/NoSQL)
  - **AI / ML & Data Engineers** (PyTorch, TensorFlow, LLMs, RAG, NLP, Spark)
  - **AI QA & QA Automation** (Pytest, Selenium, Playwright, LLM Evaluation, Ragas, DeepEval)
  - **DevOps & Cloud Engineers** (Docker, Kubernetes, AWS, Terraform, CI/CD)
- **Modern Web Application:**
  - **Light & Dark Mode Switcher:** Instant theme switching with custom design tokens.
  - **Architecture & Technical Flow Modal:** Interactive tabs with SVG system diagrams, 4-stage pipeline execution flows, and scoring rubric cards.
  - **Drag-and-Drop Resume Upload:** Native `<label>` and array-based state with removable file chips.
  - **Live Character Counter & Feedback:** Dynamic evaluation button status (`Evaluate 2 Resumes`).
- **Recruiter-Calibrated Scoring Rubric (4 Dimensions):**
  - **45% Technical Skills Match:** Direct lexical & semantic matching against Skills, Projects, and Experience sections.
  - **35% Applied Experience & Duties:** Validates hands-on execution of core job responsibilities in actual work history.
  - **10% Applied Project Justification:** Bonus for skills substantiated in real project descriptions and accomplishments rather than merely listed in keyword blocks.
  - **10% Years of Experience (YoE) Fit:** Adaptive domain duration verification matching relevant work duration against JD minimums.
- **Sigmoidal ATS Calibration Curve:** Eliminates artificially depressed scores; candidates matching $\ge 50\%$ core requirements scale to realistic scores ($75-85\%$).
- **Stopword & Action Verb Filtering:** Filters non-technical action verbs (`using`, `hands`, `experience`, `knowledge`, `build`, `develop`) preventing generic inflation.
- **Executive Reporting & Gap Analysis:** Clean output showing Candidate Rankings, Scores, Matched Skills, and Unmatched Skills (Gaps) without formula essays or unneeded columns.

---

## Setup & Installation

### 1. Prerequisites
- **Python 3.10** or newer

### 2. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## Usage

### 1. Web Application (Recommended)

Start the web application:
```powershell
python main.py
```
*(or specify a custom port: `python main.py --port 8080`)*

If port `8000` is reserved or blocked on Windows, the server **automatically finds an available port** (e.g. `8080` or `8001`) and outputs the browser link:
```text
=======================================================
  Resume Analyser Web Server Running
  Open in your browser: http://localhost:8080
=======================================================
```

#### How to use the Web UI:
1. **Upload Resumes:** Drag and drop one or more resume files into the upload box (or click anywhere in the box to browse).
2. **Paste Job Description:** Paste the complete text of the job description into the Step 2 text area.
3. **Click "Evaluate & Match Resumes":** The engine analyzes resumes, computes calibrated scores, saves `outputs/scoring_report.md`, and renders the executive report and gap analysis.
4. **Inspect Architecture & Flow:** Click **Architecture & Flow** in the top navigation bar to view the system topology, technical execution pipeline, and rubric breakdown.
5. **Toggle Themes:** Click **☀️ Light / 🌙 Dark** in the header to switch themes instantly.

---

### 2. Command Line Interface (CLI)

#### Score all resumes in `Resume/` against a Job Description:
```powershell
python main.py Resume --jd Resume/job_description.txt
```

#### Score a specific resume:
```powershell
python main.py Resume/MonalisaResume.docx --jd Resume/job_description.txt
```

#### Extract resumes without scoring (produces .md and .json in `outputs/`):
```powershell
python main.py Resume --output-dir outputs
```

#### Custom Weights & Scoring Thresholds:
You can override default weights by passing a custom JSON configuration:
```powershell
python main.py Resume --jd Resume/job_description.txt --scoring-config scoring.json
```

---

## Scoring Logic & Algorithms

### 1. Balanced Recruiter Rubric (4 Dimensions)

| Dimension | Weight | Verification Criteria |
| :--- | :---: | :--- |
| **Technical Skills Match** | **45%** | Hybrid BM25 lexical ($75\%$) + Dense semantic embeddings ($25\%$). Uses an ATS sigmoidal curve mapping raw matches $\ge 50\%$ to $75-85\%$. Searches across Skills, Projects, and Experience. |
| **Applied Experience & Duties** | **35%** | Evaluates work history against core JD responsibilities. Prioritizes professional work depth ($1.0\times$) and projects ($0.95\times$) with recency decay for older roles. |
| **Applied Project Justification** | **10%** | Awards bonus points when claimed technical skills are proven in actual project bullets or work history rather than only listed in raw keyword bullets. |
| **Years of Experience (YoE) Fit** | **10%** | Compares candidate verified domain duration (Frontend, Full Stack, Backend, DevOps, AI/ML, QA) against JD minimums (e.g. 2–5 years). Gives 100% credit when meeting or exceeding the minimum. |

### 2. Hybrid Evidence Matching
For each requirement in the job description:
- **BM25 Lexical Score:** Measures keyword presence, term frequency, and inverted document frequency across resume passages.
- **Dense Semantic Score:** Cosine similarity computed via `sentence-transformers/all-MiniLM-L6-v2`.
- **Blend Weights:**
  - **Skills:** $75\%$ Lexical $+$ $25\%$ Semantic
  - **Experience & Summary:** $20\%$ Lexical $+$ $80\%$ Semantic

### 3. Context Adjustments (Depth & Recency)
- **Section Depth:** Work experience ($1.0\times$), Projects ($0.95\times$), Certifications ($0.65\times$), Skills section ($0.85\times$), Summary ($0.4\times$).
- **Recency Decay:** Current/Present roles score $1.0$; older positions degrade by $0.07$ per year.

### 4. Adaptive Domain YoE Verification
When a requirement specifies minimum years (e.g. *"3+ years of experience"*):
- Date intervals are extracted and merged across dated work roles (cleanly handling overlapping jobs).
- The engine dynamically identifies the target domain from the requirement (QA, Frontend, Full Stack, Backend, AI/ML, DevOps, or General Software) and verifies matching role duration.

---

## Output Files

For every analysis run, files are saved in the `outputs/` directory:
- `outputs/<filename>.md` — Normalized full Markdown conversion of the resume.
- `outputs/<filename>.json` — Structured JSON containing extracted sections (`skills`, `experience`, `projects`, `summary`, etc.) and extraction warnings.
- `outputs/scoring_report.md` — The clean executive evaluation report including:
  1. Candidate ranking table (Rank, Candidate, Overall Score, Skills Match, Experience Match, Project Justification, YoE Fit)
  2. Matched requirements and skills
  3. **Missing from Resume (Gaps)** table highlighting absent skills and specific missing keywords

---

## API Reference

The FastAPI backend exposes the following endpoints:

### `GET /`
Serves the frontend single-page application with `no-cache` development headers.

### `GET /api/health`
Health check endpoint. Returns `{"status": "ok"}`.

### `POST /api/analyse`
Uploads resumes and job description text for scoring.
- **Request:** `multipart/form-data`
  - `files`: One or more document files (`.pdf`, `.docx`, `.txt`, etc.)
  - `jd_text`: String containing the job description text
- **Response:** JSON
  ```json
  {
    "success": true,
    "markdown": "# Resume Scoring Report\n..."
  }
  ```

---

## Running Unit Tests

Run the test suite using Python's built-in `unittest`:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
