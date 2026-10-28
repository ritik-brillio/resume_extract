# Resume Extractor

A small Python command-line tool that converts a resume into Markdown and extracts contact details and recognizable resume sections into JSON. Extraction uses deterministic rules and does not use an LLM or score the resume against a job description.

## Project files

- `main.py` — command-line entry point and saves the Markdown and JSON output files.
- `document_converter.py` — validates the input file and converts it to normalized Markdown with MarkItDown.
- `resume_extractor.py` — detects contact details and groups extracted text into resume sections.

## Requirements

- Python 3.10 or newer
- Dependencies listed in `requirements.txt`

MarkItDown's optional dependencies determine which formats can be converted. Scanned or image-only PDFs may need OCR; this tool does not run OCR.

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

Put one or more resumes in the `Resume` folder, then run from the project directory:

```powershell
python main.py
```

The default input is the `Resume` folder. The program processes every supported
file directly inside it and creates a Markdown and JSON output for each resume
in `outputs`. Files in subfolders are not included.

You can also provide a specific file or a different folder:

```powershell
python main.py Resume\resume.pdf --output-dir outputs
python main.py Resume --output-dir outputs
```

`--output-dir` is optional and defaults to `outputs`. Each resume's output files
use its filename, for example `resume.pdf` produces `resume.md` and
`resume.json`. If different input files have the same name without the
extension, their outputs include the original extension to keep them distinct.
The output directory must be different from the input folder.

For each input, the tool writes a Markdown and JSON file:

- `resume.md` — extracted text in Markdown format.
- `resume.json` — the Markdown text, detected contact details, grouped sections, extraction warnings, and scoring status.

When processing a folder, a conversion error for one file is reported and the
remaining files are still processed. The command exits with an error status if
any file could not be processed.

## Supported input extensions

`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`, `.html`, and `.csv`.

Input files must exist and be no larger than 15 MB. Unsupported formats and files over the size limit are rejected.

## What is extracted

- Email addresses, likely phone numbers, and URLs are detected with regular expressions. Phone matching is approximate. URLs are detected when they start with `http://`, `https://`, or `www.`, and bare LinkedIn and GitHub profile links are also recognized.
- Common headings are used to group text into sections such as summary, skills (including “Core Skills”), experience, projects, research, achievements, education, and certifications. Unrecognized text is preserved in an `other` section.
- Page-break characters are removed, and words split by a hyphen at a line break are joined when the continuation starts with a lowercase letter.
- If no text is extracted, or very little text is extracted from a PDF, the program prints a warning. A warning does not mean OCR was performed.

Section and contact detection are heuristic, so results may not be complete or perfectly categorized. The full extracted text is included in the JSON file.

## Job-description scoring

Job-description scoring is not implemented. The JSON `scoring_status` is currently `not_implemented`. See [docs/scoring-design.md](docs/scoring-design.md) for a proposed future design.

## Privacy

Resume output files contain personal information, including the full extracted text and detected contact details. Store and share them carefully.
