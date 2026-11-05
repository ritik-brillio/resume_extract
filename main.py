import argparse
import sys
from pathlib import Path

from backend.document_converter import SUPPORTED_EXTENSIONS
from backend.jd_parser import RequirementWeights, parse_job_description_file
from backend.matching_engine import (
    CandidateScore,
    ScoringConfiguration,
    score_candidate,
)
from backend.resume_chunker import chunk_resume_sections
from backend.resume_extractor import ResumeData, parse_resume
from backend.scoring_report import build_scoring_report, render_scoring_report


def save_outputs(
    resume: ResumeData,
    output_dir: Path,
    output_stem: str | None = None,
) -> tuple[Path, Path]:
    """Save full Markdown and structured JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_stem or Path(resume.source_filename).stem

    markdown_path = output_dir / f"{stem}.md"
    json_path = output_dir / f"{stem}.json"

    markdown_path.write_text(resume.markdown, encoding="utf-8")
    json_path.write_text(
        resume.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return markdown_path, json_path


def collect_input_files(input_path: Path, output_dir: Path) -> list[Path]:
    """Return one input file or supported files directly inside a folder."""
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")
    if input_path.resolve() == output_dir.resolve():
        raise ValueError(
            "The output directory must be different from the input directory."
        )

    files = sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        raise ValueError(
            f"No supported resume files found in {input_path}."
        )
    return files


def resolve_job_description_path(jd_argument: str, input_path: Path) -> Path:
    """Resolve a JD from the current directory or alongside the resume input."""
    jd_path = Path(jd_argument)
    if jd_path.exists() or jd_path.is_absolute():
        return jd_path

    input_directory = input_path if input_path.is_dir() else input_path.parent
    alongside_input = input_directory / jd_path
    if alongside_input.exists():
        return alongside_input
    return jd_path


def run_cli(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    config = ScoringConfiguration()
    job_description = None
    jd_path: Path | None = None
    try:
        if args.scoring_config:
            config_path = Path(args.scoring_config)
            config = ScoringConfiguration.model_validate_json(
                config_path.read_text(encoding="utf-8")
            )
        if config.chunk_overlap_words >= config.max_chunk_words:
            raise ValueError(
                "chunk_overlap_words must be less than max_chunk_words."
            )
        if args.jd:
            jd_path = resolve_job_description_path(args.jd, input_path)
            job_description = parse_job_description_file(
                jd_path,
                RequirementWeights(
                    mandatory=config.mandatory_weight,
                    preferred=config.preferred_weight,
                    unspecified=config.unspecified_weight,
                ),
            )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        input_files = collect_input_files(input_path, output_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if job_description and jd_path:
        jd_path = jd_path.resolve()
        input_files = [
            path for path in input_files if path.resolve() != jd_path
        ]
        if not input_files:
            print("Error: No resume files remain after excluding the job description.", file=sys.stderr)
            sys.exit(2)

    stem_counts: dict[str, int] = {}
    for path in input_files:
        key = path.stem.casefold()
        stem_counts[key] = stem_counts.get(key, 0) + 1

    input_paths = {path.resolve() for path in input_files}
    failures = 0
    candidate_scores: list[CandidateScore] = []
    for path in input_files:
        output_stem = (
            path.name if stem_counts[path.stem.casefold()] > 1 else path.stem
        )
        output_paths = (
            output_dir / f"{output_stem}.md",
            output_dir / f"{output_stem}.json",
        )
        try:
            if any(output.resolve() in input_paths for output in output_paths):
                raise ValueError(
                    "Output would overwrite an input file; choose a different "
                    "--output-dir."
                )

            resume = parse_resume(path)
            if job_description:
                resume.scoring_status = "reported_separately"
            markdown_path, json_path = save_outputs(
                resume, output_dir, output_stem
            )

            candidate_score = None
            if job_description:
                extracted_resume = ResumeData.model_validate_json(
                    json_path.read_text(encoding="utf-8")
                )
                chunks = chunk_resume_sections(
                    extracted_resume.sections,
                    max_words=config.max_chunk_words,
                    overlap_words=config.chunk_overlap_words,
                )
                candidate_score = score_candidate(
                    source_filename=resume.source_filename,
                    requirements=job_description.requirements,
                    chunks=chunks,
                    extraction_warnings=resume.extraction_warnings,
                    config=config,
                )
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Error processing {path}: {exc}", file=sys.stderr)
            failures += 1
            continue

        print(f"Markdown saved: {markdown_path}")
        print(f"JSON saved: {json_path}")

        for warning in resume.extraction_warnings:
            print(f"Warning ({path.name}): {warning}")
        if candidate_score:
            candidate_scores.append(candidate_score)

    if job_description and candidate_scores:
        try:
            report = build_scoring_report(
                job_description,
                candidate_scores,
                config,
                job_description_source=jd_path.name if jd_path else None,
            )
            report_path = output_dir / "scoring_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_scoring_report(report), encoding="utf-8")
            print(f"Scoring report saved: {report_path}")
            for candidate in report.candidates:
                print(
                    f"{candidate.rank}. {candidate.source_filename}: "
                    f"{candidate.overall_score:.2f}% "
                    f"(strong: {len(candidate.matched_requirements)}, "
                    "partial/uncertain: "
                    f"{len(candidate.partial_or_uncertain_requirements)}, "
                    "no evidence: "
                    f"{len(candidate.no_evidence_requirements)})"
                )
                for category_score in candidate.category_scores:
                    print(
                        f"   {category_score.category}: "
                        f"{category_score.score_percentage:.2f}% "
                        f"({category_score.requirement_count} requirements)"
                    )
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Error saving scoring report: {exc}", file=sys.stderr)
            failures += 1

    if failures:
        sys.exit(1)


def find_available_port(preferred_port: int, host: str = "127.0.0.1") -> int:
    """Check if preferred_port is bindable, or find the next free candidate."""
    import socket

    def is_port_free(port_to_test: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port_to_test))
                return True
            except OSError:
                return False

    if is_port_free(preferred_port):
        return preferred_port

    candidates = [8080, 8001, 8501, 5000, 3000, 8888]
    for candidate in candidates:
        if candidate != preferred_port and is_port_free(candidate):
            print(
                f"Note: Port {preferred_port} is restricted or in use on this machine. "
                f"Auto-selected available port {candidate}."
            )
            return candidate

    return preferred_port


def start_server(port: int = 8000, host: str = "127.0.0.1") -> None:
    import uvicorn

    active_port = find_available_port(port, host)
    print(f"\n=======================================================")
    print(f"  Resume Analyser Web Server Running")
    print(f"  Open in your browser: http://localhost:{active_port}")
    print(f"=======================================================\n")
    uvicorn.run("backend.api:app", host=host, port=active_port, reload=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract and score resumes via CLI or run the web interface."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="Resume",
        help="Resume file or folder (default: Resume)",
    )
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument(
        "--jd",
        help="Job description file; enables requirement-level resume scoring",
    )
    parser.add_argument(
        "--scoring-config",
        help="Optional JSON file overriding requirement weights and thresholds",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the web UI and API server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the web server on (default: 8000, falls back to free port if blocked)",
    )
    args = parser.parse_args()

    # If explicitly asked to serve, or no arguments were passed (just `python main.py`)
    if args.serve or len(sys.argv) == 1:
        start_server(port=args.port)
    elif args.jd:
        if args.scoring_config and not args.jd:
            parser.error("--scoring-config requires --jd.")
        run_cli(args)
    else:
        # If user passed positional argument or other flags without --jd
        run_cli(args)


if __name__ == "__main__":
    main()
