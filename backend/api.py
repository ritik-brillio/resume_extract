import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .document_converter import SUPPORTED_EXTENSIONS
from .jd_parser import RequirementWeights, parse_job_description
from .matching_engine import CandidateScore, ScoringConfiguration, score_candidate
from .resume_chunker import chunk_resume_sections
from .resume_extractor import ResumeData, parse_resume
from .scoring_report import build_scoring_report, render_scoring_report

BASE_DIR = Path(__file__).parent.parent
RESUME_DIR = BASE_DIR / "Resume"
OUTPUT_DIR = BASE_DIR / "outputs"
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Resume Analyser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(
        str(FRONTEND_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyse")
async def analyse(
    files: list[UploadFile] = File(...),
    jd_text: str = Form(""),
    must_have_skills: str = Form(""),
    good_to_have_skills: str = Form(""),
) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No resume files uploaded.")
    if not jd_text.strip() and not must_have_skills.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a Job Description or specify Must-Have Skills.",
        )

    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Validate and save uploaded resumes
    saved_paths: list[Path] = []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}' for '{upload.filename}'. "
                       f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )
        dest = RESUME_DIR / (upload.filename or f"upload{suffix}")
        with dest.open("wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved_paths.append(dest)

    try:
        config = ScoringConfiguration()

        # Parse JD from pasted text and explicit skill inputs
        job_description = parse_job_description(
            jd_text,
            RequirementWeights(
                mandatory=config.mandatory_weight,
                preferred=config.preferred_weight,
                unspecified=config.unspecified_weight,
            ),
            must_have_skills=must_have_skills,
            good_to_have_skills=good_to_have_skills,
        )

        candidate_scores: list[CandidateScore] = []
        for path in saved_paths:
            resume = parse_resume(path)
            resume.scoring_status = "reported_separately"

            # Save per-resume outputs (md + json)
            stem = path.stem
            md_path = OUTPUT_DIR / f"{stem}.md"
            json_path = OUTPUT_DIR / f"{stem}.json"
            md_path.write_text(resume.markdown, encoding="utf-8")
            json_path.write_text(resume.model_dump_json(indent=2), encoding="utf-8")

            # Score candidate
            extracted = ResumeData.model_validate_json(
                json_path.read_text(encoding="utf-8")
            )
            chunks = chunk_resume_sections(
                extracted.sections,
                max_words=config.max_chunk_words,
                overlap_words=config.chunk_overlap_words,
            )
            score = score_candidate(
                source_filename=resume.source_filename,
                requirements=job_description.requirements,
                chunks=chunks,
                extraction_warnings=resume.extraction_warnings,
                config=config,
            )
            candidate_scores.append(score)

        # Build and save scoring report
        report = build_scoring_report(
            job_description,
            candidate_scores,
            config,
            job_description_source="Provided job description",
        )
        report_md = render_scoring_report(report)
        report_path = OUTPUT_DIR / "scoring_report.md"
        report_path.write_text(report_md, encoding="utf-8")

        return JSONResponse({
            "success": True,
            "markdown": report_md,
            "report": report.model_dump(),
        })

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")
