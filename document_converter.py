import re
from pathlib import Path

from markitdown import MarkItDown

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".txt", ".md", ".html", ".csv",
}
MAX_FILE_SIZE = 15 * 1024 * 1024 # 15 MB 


def normalize_text(text: str) -> str:
    """Normalize whitespace while preserving Markdown structure."""
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\f", "\n")
    text = re.sub(
        r"(?<=[A-Za-z])-\n(?:[ \t]*\n)*[ \t]*(?=[a-z])",
        "",
        text,
    )
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def convert_to_markdown(file_path: Path) -> tuple[str, list[str]]:
    """Convert a supported document into Markdown without an LLM."""
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 15 MB limit.")

    result = MarkItDown().convert(str(file_path))
    markdown = normalize_text(result.text_content or "")
    warnings = []

    if not markdown:
        warnings.append(
            "No text extracted. The document may be scanned or empty; OCR may be required."
        )
    elif file_path.suffix.lower() == ".pdf" and len(markdown) < 100:
        warnings.append("Very little PDF text extracted; check whether OCR is needed.")

    return markdown, warnings
