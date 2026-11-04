# Resume Extractor & Scoring Engine

An AI-powered, deterministic resume extraction and scoring system. It converts multi-format resumes into clean Markdown, extracts structured sections into JSON, and scores candidates against job descriptions using a hybrid lexical (BM25) and local dense semantic embedding model (`all-MiniLM-L6-v2`).

It features both an **interactive Web UI** (multi-file drag-and-drop, real-time Markdown rendering, candidate ranking, and gap analysis) and a **command-line interface (CLI)**.

---

## Architecture & Project Structure

```text
resume_extract/
├── backend/                    # Core Python application modules
│   ├── __init__.py
│   ├── api.py                  # FastAPI REST server & static file router
│   ├── document_converter.py   # Document conversion to Markdown (MarkItDown)
│   ├── jd_parser.py            # JD clause splitting, category & priority detection
│   ├── matching_engine.py      # Hybrid BM25 + dense semantic scoring & 1/N fallback
│   ├── resume_chunker.py       # Section passage segmentation & date metadata
│   ├── resume_extractor.py     # Section heading mapping & contact extraction
│   └── scoring_report.py       # Ranked scoring report & gap analysis generation
├── frontend/                   # Web user interface assets
│   ├── index.html              # Modern dark-mode UI layout
│   ├── css/style.css           # Styling for tables, chips, upload zones, and cards
│   └── js/app.js               # Multi-upload logic, API caller, and marked.js renderer
├── Resume/                     # Input folder for resumes and JD documents
├── outputs/                    # Output directory for .md, .json, and scoring_report.md
├── tests/                      # Unit test suite
│   └── test_resume_extractor.py
├── docs/                       # Architectural documentation
│   └── scoring-design.md
├── main.py                     # Unified entry point (Web server & CLI)
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## Key Features

- **Multi-Format Support:** Converts `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`, `.html`, and `.csv` up to 15 MB.
- **Privacy-First & Fully Local:** Uses local Sentence Transformers (`all-MiniLM-L6-v2`) and BM25. No data is sent to external LLMs or third-party APIs.
- **Web UI:**
  - Drag-and-drop multi-file resume uploader with removable chips.
  - Pasteable job description input with live character counter.
  - Real-time animated analysis state.
  - Formatted results display rendered directly from the generated Markdown report.
- **Priority Detection with 1/N Fallback:**
  - Automatically identifies **Mandatory** vs. **Preferred** requirements based on explicit keywords and section headers.
  - When no explicit priorities are detected, dynamically falls back to **equal $1/N$ weighting** across requirements within each section.
- **Gap Analysis:** Pinpoints exactly what skills and requirements are missing from the resume, highlighting the specific missing keywords.
- **Auditable & Deterministic:** Every score is backed by extracted evidence passages, section depth, recency ratings, and date-range estimates.

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

If port `8000` is reserved or in use on your Windows machine, the server **automatically detects an available port** (e.g. `8080`) and prints the direct browser URL:
```text
=======================================================
  Resume Analyser Web Server Running
  Open in your browser: http://localhost:8080
=======================================================
```

#### How to use the Web UI:
1. **Upload Resumes:** Drag and drop one or more resume files into the upload box (or click to browse).
2. **Paste Job Description:** Paste the complete text of the job description into the text area.
3. **Click "Analyse Resumes":** The backend processes the resumes, calculates scores, generates `outputs/scoring_report.md`, and renders the full report with gap analysis directly on the page.

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

### 1. Hybrid Evidence Matching
For each requirement in the job description:
- **BM25 Lexical Score:** Measures keyword presence, term frequency, and inverted document frequency across resume passages.
- **Dense Semantic Score:** Cosine similarity computed via `sentence-transformers/all-MiniLM-L6-v2`.
- **Blend Weights:**
  - **Skills:** $75\%$ Lexical $+$ $25\%$ Semantic
  - **Experience & Summary:** $20\%$ Lexical $+$ $80\%$ Semantic

### 2. Context Adjustments (Depth & Recency)
- **Section Depth (20%):** Higher credit for evidence found in work experience ($1.0$), projects ($0.85$), or certifications ($0.65$) vs. simple skill lists ($0.4$).
- **Recency (10%):** Current/Present roles score $1.0$; older positions degrade by $0.07$ per year past current year.

### 3. Duration & Years of Experience (70% for Duration Requirements)
When a requirement specifies minimum years (e.g., *"3+ years of experience in QA"*):
- Work experience intervals are extracted from dated resume passages (handling overlapping dates cleanly).
- Testing/QA-specific requirements verify relevant role titles or descriptions.
- The requirement match score blends the evidence match ($30\%$) and the dated duration fraction ($70\%$).

### 4. Priority Weighting & 1/N Fallback

| Priority | Weight | Keyword Triggers |
| :--- | :---: | :--- |
| **Mandatory** | `3.0` | `must`, `required`, `mandatory`, `essential`, `minimum`, `at least`, or headings like `Must Have:`, `Required Skills:` |
| **Preferred** | `1.0` | `preferred`, `preferably`, `nice to have`, `bonus`, `desirable`, or headings like `Nice to Have:` |
| **Unspecified** | `2.0` | Default when no keywords or explicit headings match. |

#### Fallback Condition:
If **no requirements** in the category contain explicit mandatory or preferred keywords (i.e. all are unspecified), the engine applies **equal $1/N$ weights**:
$$\text{Weight}_i = \frac{1}{N} \quad (\text{for each requirement } i=1 \dots N)$$
$$\text{Category Score} = \frac{1}{N} \sum_{i=1}^N \text{Score}_i$$

### 5. Overall Candidate Score
Overall candidate ranking combines section scores using calibrated category weights:
- **Experience:** $\approx 70.59\%$
- **Skills:** $\approx 23.53\%$
- **Summary:** $\approx 5.88\%$
- *(Education requirements are excluded from scoring)*

---

## Output Files

For every analysis run, files are saved in the `outputs/` directory:
- `outputs/<filename>.md` — Normalized full Markdown conversion of the resume.
- `outputs/<filename>.json` — Structured JSON containing extracted sections (`skills`, `experience`, `projects`, `summary`, etc.) and extraction warnings.
- `outputs/scoring_report.md` — The complete evaluation report including:
  1. Candidate ranking summary table
  2. Section score breakdowns
  3. Requirement-by-requirement score, status, and supporting evidence excerpts
  4. **Missing from Resume (Gaps)** table highlighting absent skills and exact missing keywords
  5. Experience verification notes

---

## API Reference

The FastAPI backend exposes the following endpoints:

### `GET /`
Serves the frontend single-page application.

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
