import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResumeChunk:
    chunk_id: str
    source_section: str
    text: str
    company_name: str | None = None
    date_range: str | None = None


_MONTH_PATTERN = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?"
)
_DATE_RANGE_PATTERN = re.compile(
    rf"\b(?:(?:{_MONTH_PATTERN})\s+)?(?:19|20)\d{{2}}\s*"
    rf"(?:[-–—\ufffd]|to)\s*"
    rf"(?:present|current|(?:(?:{_MONTH_PATTERN})\s+)?"
    rf"(?:19|20)\d{{2}})\b",
    re.IGNORECASE,
)


def _extract_metadata(
    section: str,
    passage: str,
) -> tuple[str | None, str | None]:
    date_match = _DATE_RANGE_PATTERN.search(passage)
    date_range = date_match.group(0) if date_match else None
    company_match = None
    if section == "experience":
        company_match = re.search(
            r"^\s*([A-Z][A-Za-z0-9&.,' -]{2,50}?)\s+\|\s+[A-Z]",
            passage,
        )
    company_name = (
        company_match.group(1).strip(" .,-")
        if company_match
        else None
    )
    return company_name, date_range


def _clean_passage(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(line.strip() for line in lines)).strip()


def _split_large_passage(
    text: str,
    max_words: int,
    overlap_words: int,
) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]

    passages: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        passages.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words
    return passages


def chunk_resume_sections(
    sections: dict[str, str],
    max_words: int = 120,
    overlap_words: int = 0,
) -> list[ResumeChunk]:
    """Split extracted JSON sections into section-tagged evidence passages."""
    if max_words < 1 or overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("Chunk limits must satisfy 0 <= overlap < max_words.")

    blocks: list[tuple[str, str, str | None, str | None]] = []
    for section, section_text in sections.items():
        current_company: str | None = None
        current_date_range: str | None = None
        current_lines: list[str] = []

        def flush() -> None:
            passage = _clean_passage(current_lines)
            if passage:
                company_name, date_range = _extract_metadata(section, passage)
                blocks.append(
                    (
                        section,
                        passage,
                        company_name or current_company,
                        date_range or current_date_range,
                    )
                )
            current_lines.clear()

        for line in section_text.splitlines():
            if not line.strip():
                flush()
            elif re.match(r"^\s*(?:[-*+•]|\d+[.)])\s+", line):
                flush()
                current_lines.append(line)
            else:
                current_lines.append(line)

            if section == "experience":
                company_name, date_range = _extract_metadata(section, line)
                if company_name:
                    current_company = company_name
                if date_range:
                    current_date_range = date_range
        flush()

    merged_blocks: list[tuple[str, str, str | None, str | None]] = []
    for section, passage, company_name, date_range in blocks:
        if (
            len(passage.split()) <= 3
            and merged_blocks
            and merged_blocks[-1][0] == section
        ):
            previous_section, previous_text, old_company, old_date = merged_blocks[-1]
            merged_blocks[-1] = (
                previous_section,
                f"{previous_text} {passage}",
                old_company or company_name,
                old_date or date_range,
            )
        else:
            merged_blocks.append((section, passage, company_name, date_range))

    chunks: list[ResumeChunk] = []
    for section, passage, company_name, date_range in merged_blocks:
        for split_passage in _split_large_passage(
            passage, max_words, overlap_words
        ):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"chunk-{len(chunks) + 1}",
                    source_section=section,
                    text=split_passage,
                    company_name=company_name,
                    date_range=date_range,
                )
            )
    return chunks
