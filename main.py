import argparse
import sys
from pathlib import Path

from document_converter import SUPPORTED_EXTENSIONS
from resume_extractor import ResumeData, parse_resume


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract one resume or all supported files in a folder."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="Resume",
        help="Resume file or folder (default: Resume)",
    )
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    try:
        input_files = collect_input_files(input_path, output_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))

    stem_counts: dict[str, int] = {}
    for path in input_files:
        key = path.stem.casefold()
        stem_counts[key] = stem_counts.get(key, 0) + 1

    input_paths = {path.resolve() for path in input_files}
    failures = 0
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
            markdown_path, json_path = save_outputs(
                resume, output_dir, output_stem
            )
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Error processing {path}: {exc}", file=sys.stderr)
            failures += 1
            continue

        print(f"Markdown saved: {markdown_path}")
        print(f"JSON saved: {json_path}")

        for warning in resume.extraction_warnings:
            print(f"Warning ({path.name}): {warning}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
