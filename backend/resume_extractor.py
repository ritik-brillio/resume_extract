import re
from pathlib import Path

from pydantic import BaseModel, Field

from .document_converter import convert_to_markdown

# Common section headings
EXCLUDED_SECTION_CATEGORIES = {"research", "achievements"}

SECTION_ALIASES = {
    "summary": {
        "summary", "professional summary", "profile", "objective"
    },
    "skills": {
        "skills", "skill set", "technical skills", "core skills",
        "core competencies", "key skills",
        "key skills & technical skills",
        "technologies", "tech stack", "technical proficiencies",
        "tools & technologies", "tools and technologies",
        "technical expertise", "programming languages",
        "development skills", "frameworks & libraries",
        "technical tools",
    },
    "experience": {
        "experience", "work experience", "professional experience",
        "employment history", "work history",
        "experience and work history",
    },
    "education": {
        "education", "academic background", "qualifications"
    },
    "projects": {
        "projects", "personal projects", "academic projects",
        "flagship project", "additional projects", "project details",
        "key projects", "selected projects", "project experience",
        "relevant projects", "client projects", "major projects",
        "industry projects",
    },
    "certifications": {
        "certifications", "certificates", "licenses"
    },
    "achievements": {"achievements", "awards", "honors"},
    "research": {"research", "research experience"},
}


class ContactDetails(BaseModel):
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    source_filename: str
    markdown: str = Field(default="", exclude=True)
    sections: dict[str, str]
    extraction_warnings: list[str] = Field(default_factory=list)
    scoring_status: str = "not_requested"


def extract_contact(markdown: str) -> ContactDetails:
    """Extract contact candidates using regex."""
    emails = re.findall(
        r"(?i)(?<![\\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\\w.-])",
        markdown,
    )

    urls = re.findall(
        r"(?i)(?:\b(?:https?://|www\.)[^\s<>()\]]+|"
        r"(?<![@\w.-])(?:linkedin\.com|github\.com)"
        r"(?:/[^\s<>()\]]*)?)",
        markdown,
    )
    urls = [url.rstrip(".,;:") for url in urls]

    # Phone matching is approximate
    candidates = re.findall(
        r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?"
        r"(?:\(?\d{2,5}\)?[\s.-]?)\d{3,5}[\s.-]?\d{3,5}(?!\w)",
        markdown,
    )

    phones = []
    for candidate in candidates:
        digits = re.sub(r"\D", "", candidate)
        if 8 <= len(digits) <= 15 and candidate.strip() not in phones:
            phones.append(candidate.strip())

    return ContactDetails(
        emails=list(dict.fromkeys(email.lower() for email in emails)),
        phones=phones,
        urls=list(dict.fromkeys(urls)),
    )


def match_section_heading(line: str) -> str | None:
    """Return a known section for a heading line, if one matches."""
    raw = line.strip()
    heading = re.sub(r"^\s{0,3}#{1,6}\s*", "", raw)
    heading = re.sub(r"[*_`]", "", heading).strip().rstrip(":").lower()
    heading = re.sub(r"\s+", " ", heading)

    if heading == "project details" and not (raw.isupper() or raw.startswith("#")):
        return None

    return next(
        (
            name
            for name, aliases in SECTION_ALIASES.items()
            if heading in aliases
        ),
        None,
    )


def extract_sections(markdown: str) -> dict[str, str]:
    """Split text by recognizable headings and preserve everything else."""
    sections: dict[str, list[str]] = {"other": []}
    current_section = "other"

    for line in markdown.splitlines():
        matched_section = match_section_heading(line)
        if matched_section:
            current_section = matched_section
            sections.setdefault(current_section, [])
        else:
            sections[current_section].append(line)

    # Keep excluded sections in Markdown without adding them to JSON sections.
    return {
        name: content
        for name, lines in sections.items()
        if name not in {"other", *EXCLUDED_SECTION_CATEGORIES}
        and (content := "\n".join(lines).strip())
    }


def parse_resume(file_path: Path) -> ResumeData:
    """Convert a resume and extract its structured data."""
    markdown, warnings = convert_to_markdown(file_path)

    return ResumeData(
        source_filename=file_path.name,
        markdown=markdown,
        sections=extract_sections(markdown),
        extraction_warnings=warnings,
    )
