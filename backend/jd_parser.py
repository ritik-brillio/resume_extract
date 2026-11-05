import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .document_converter import convert_to_markdown

RequirementCategory = Literal[
    "skills",
    "experience",
    "summary",
    "education",
]
RequirementPriority = Literal["mandatory", "preferred", "unspecified"]


class JDRequirement(BaseModel):
    requirement_id: str
    text: str
    category: RequirementCategory
    weight: float = Field(gt=0)
    priority: RequirementPriority
    source_text: str
    minimum_years: float | None = Field(default=None, ge=0)


class JobDescription(BaseModel):
    original_text: str
    requirements: list[JDRequirement]
    extraction_warnings: list[str] = Field(default_factory=list)


class RequirementWeights(BaseModel):
    mandatory: float = Field(default=3.0, gt=0)
    preferred: float = Field(default=1.0, gt=0)
    unspecified: float = Field(default=2.0, gt=0)


def _clean_line(line: str) -> str:
    line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line.strip())
    line = re.sub(r"^\s*(?:[-*+•]|\d+[.)])\s*", "", line)
    return re.sub(r"[*_`]", "", line).strip()


def _is_section_header(line: str) -> tuple[bool, str, RequirementCategory | None, RequirementPriority | None]:
    """Identify if a line is a section header, metadata, or title (not a requirement)."""
    raw_cleaned = _clean_line(line)
    cleaned = raw_cleaned.rstrip(":").casefold()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # 1. Title or document metadata lines to skip completely
    if re.match(
        r"^(?:job\s+description|job\s+title|role\s+title|position\s+title|about\s+us|about\s+the\s+company|company\s+overview)\b",
        cleaned,
    ):
        return True, "skip", None, None
    if re.match(r"^(?:role|location|job\s+type|employment\s+type)\s*:", cleaned):
        return True, "skip", None, None
    if line.strip().startswith("# ") and re.search(r"\b(?:developer|engineer|architect|specialist|consultant|manager|lead|tester)\b", cleaned):
        return True, "skip", None, None

    # If the line contains a colon and substantive content after it, it's an inline requirement, not a section header
    if ":" in raw_cleaned:
        prefix, after_colon = raw_cleaned.split(":", 1)
        if after_colon.strip():
            return False, "requirement", None, None

    # 2. Responsibilities / Experience section
    if re.match(
        r"^(?:key\s+responsibilities|core\s+responsibilities|responsibilities|what\s+you(?:ll|\s+will)\s+do|duties|role\s+overview|day\s+in\s+the\s+life)\b",
        cleaned,
    ):
        return True, "header", "experience", "mandatory"

    # 3. Mandatory / Required technical skills
    if re.match(
        r"^(?:required\s+technical\s+skills|required\s+skills|mandatory\s+skills|must\s+have|technical\s+skills|"
        r"core\s+skills|key\s+skills|requirements|qualifications|required\s+qualifications|job\s+requirements|"
        r"minimum\s+qualifications|tech\s+stack|technologies|technical\s+requirements|tools\s+and\s+technologies|"
        r"skills\s+required|what\s+you\s+need|what\s+we(?:re|\s+are)\s+looking\s+for|skills\s+and\s+experience)\b",
        cleaned,
    ):
        return True, "header", "skills", "mandatory"

    # 4. Preferred / Good to have skills
    if re.match(
        r"^(?:good\s+to\s+have|nice\s+to\s+have|nice-to-have|preferred\s+skills|preferred\s+technical\s+skills|"
        r"preferred\s+qualifications|preferred|desirable|bonus|plus|what\s+gives\s+you\s+an\s+edge)\b",
        cleaned,
    ):
        return True, "header", "skills", "preferred"

    # 5. Experience specific headers
    if re.match(r"^(?:required\s+experience|experience|professional\s+experience|work\s+experience|prior\s+experience)\b", cleaned):
        return True, "header", "experience", "mandatory"

    # 6. Summary / Role overview headers
    if re.match(r"^(?:summary|job\s+summary|role\s+summary|position\s+overview|about\s+the\s+role|who\s+you\s+are)\b", cleaned):
        return True, "header", "summary", "unspecified"

    # 7. Education headers
    if re.match(r"^(?:education|academic\s+background|degrees|academic\s+qualifications)\b", cleaned):
        return True, "header", "education", "unspecified"

    return False, "requirement", None, None


def _classify_category(
    text: str,
    heading_category: RequirementCategory | None,
) -> RequirementCategory:
    lowered = text.casefold()
    if re.search(r"\b(?:degree|education|bachelor|master|ph\.?d|b\.?tech|m\.?tech|b\.?s|m\.?s|graduate)\b", lowered):
        return "education"

    if heading_category:
        return heading_category

    # Heuristic for unheaded requirements
    if re.search(
        r"\b(?:years\s+(?:of\s+)?experience|worked\s+(?:on|with)|hands[\s-]on\s+experience|"
        r"responsible\s+for|collaborate|architect|lead|deliver|manage|build\s+and\s+maintain|"
        r"design\s+and\s+implement|develop\s+and\s+maintain|work\s+closely)\b",
        lowered,
    ):
        return "experience"

    return "skills"


def _classify_priority(
    text: str,
    heading_priority: RequirementPriority,
) -> RequirementPriority:
    lowered = text.casefold()
    if re.search(
        r"\b(?:must|required|mandatory|essential|minimum|at least)\b",
        lowered,
    ):
        return "mandatory"
    if re.search(
        r"\b(?:preferred|preferably|nice to have|good to have|bonus|desirable)\b",
        lowered,
    ):
        return "preferred"
    return heading_priority


def _extract_minimum_years(text: str) -> float | None:
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*[-–—\ufffd]\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
            text,
            re.IGNORECASE,
        )
    return float(match.group(1)) if match else None


def _split_requirement_text(text: str) -> list[str]:
    protected_text = re.sub(
        r"\b(?:e\.g|i\.e)\.",
        lambda match: match.group().replace(".", "\0"),
        text,
        flags=re.IGNORECASE,
    )
    clauses = re.split(r"(?<=[.!?])\s+|;\s+", protected_text)
    requirements: list[str] = []
    for clause in clauses:
        clause = clause.replace("\0", ".").strip()
        if clause:
            requirements.append(clause)
    return requirements


def _parse_skill_tokens(skill_str: str | None) -> list[str]:
    if not skill_str:
        return []
    tokens = re.split(r"[,;\n•|]+", skill_str)
    result = []
    for token in tokens:
        cleaned = _clean_line(token)
        if cleaned and len(cleaned) >= 2:
            result.append(cleaned)
    return result


def append_explicit_skills(
    job_description: JobDescription,
    must_have_skills: str | None = None,
    good_to_have_skills: str | None = None,
    weights: RequirementWeights | None = None,
) -> JobDescription:
    """Merge or append user-specified Must-Have and Good-to-Have skills into the parsed JD."""
    if weights is None:
        weights = RequirementWeights()

    mh_list = _parse_skill_tokens(must_have_skills)
    gh_list = _parse_skill_tokens(good_to_have_skills)

    # 1. Process Must-Have skills (Mandatory, weight = weights.mandatory e.g. 3.0)
    for skill in mh_list:
        norm_skill = " ".join(re.findall(r"[a-z0-9+#.]+", skill.casefold()))
        matched_req = None
        for req in job_description.requirements:
            req_norm = " ".join(re.findall(r"[a-z0-9+#.]+", req.text.casefold()))
            if norm_skill == req_norm or (len(norm_skill) >= 3 and (norm_skill in req_norm or req_norm in norm_skill)):
                matched_req = req
                break

        if matched_req:
            matched_req.priority = "mandatory"
            matched_req.weight = weights.mandatory
            matched_req.category = "skills"
        else:
            req_id = f"req-mh-{len(job_description.requirements) + 1}"
            job_description.requirements.append(
                JDRequirement(
                    requirement_id=req_id,
                    text=skill,
                    category="skills",
                    weight=weights.mandatory,
                    priority="mandatory",
                    source_text=f"Explicit Must-Have: {skill}",
                    minimum_years=None,
                )
            )

    # 2. Process Good-to-Have skills (Preferred, weight = weights.preferred e.g. 1.0)
    for skill in gh_list:
        norm_skill = " ".join(re.findall(r"[a-z0-9+#.]+", skill.casefold()))
        matched_req = None
        for req in job_description.requirements:
            req_norm = " ".join(re.findall(r"[a-z0-9+#.]+", req.text.casefold()))
            if norm_skill == req_norm or (len(norm_skill) >= 3 and (norm_skill in req_norm or req_norm in norm_skill)):
                matched_req = req
                break

        if matched_req:
            if matched_req.priority != "mandatory":
                matched_req.priority = "preferred"
                matched_req.weight = weights.preferred
        else:
            req_id = f"req-gh-{len(job_description.requirements) + 1}"
            job_description.requirements.append(
                JDRequirement(
                    requirement_id=req_id,
                    text=skill,
                    category="skills",
                    weight=weights.preferred,
                    priority="preferred",
                    source_text=f"Explicit Good-to-Have: {skill}",
                    minimum_years=None,
                )
            )

    return job_description


def parse_job_description(
    text: str,
    weights: RequirementWeights | None = None,
    extraction_warnings: list[str] | None = None,
    must_have_skills: str | None = None,
    good_to_have_skills: str | None = None,
) -> JobDescription:
    """Extract clean, deterministic requirements from JD text."""
    original_text = text.strip()
    weights = weights or RequirementWeights()
    heading_priority: RequirementPriority = "unspecified"
    heading_category: RequirementCategory | None = None
    candidates: list[JDRequirement] = []
    seen: set[str] = set()
    excluded_education_count = 0

    for paragraph in re.split(r"\n\s*\n", original_text):
        source_text = paragraph.strip()
        if not source_text:
            continue
        lines = source_text.splitlines()
        for line in lines:
            raw_line = line.strip()
            if not raw_line:
                continue

            is_hdr, action, cat, prio = _is_section_header(raw_line)
            if is_hdr:
                if action == "header":
                    heading_category = cat
                    if prio:
                        heading_priority = prio
                continue

            cleaned = _clean_line(raw_line)
            if not cleaned:
                continue

            # Check inline required skills: 'Required Technical Skills: React, Node.js...', 'Key Skills: ...'
            inline_skills_match = re.match(
                r"^(?:required\s+technical\s+skills|required\s+skills|technical\s+skills|key\s+skills|core\s+skills|tech\s+stack|technologies|skills)\s*:\s*(.+)$",
                cleaned,
                re.IGNORECASE,
            )
            if inline_skills_match:
                skills_part = inline_skills_match.group(1)
                for skill in skills_part.split(","):
                    skill = skill.strip()
                    norm_skill = " ".join(re.findall(r"[a-z0-9]+", skill.casefold()))
                    if norm_skill and norm_skill not in seen:
                        seen.add(norm_skill)
                        candidates.append(
                            JDRequirement(
                                requirement_id=f"req-{len(candidates) + 1}",
                                text=skill,
                                category="skills",
                                weight=weights.mandatory,
                                priority="mandatory",
                                source_text=raw_line,
                            )
                        )
                continue

            # Check inline experience: 'Experience: 2–5 Years' or 'Required Experience: 3+ Years'
            inline_exp_match = re.match(
                r"^(?:required\s+experience|experience|work\s+experience)\s*:\s*(.+)$",
                cleaned,
                re.IGNORECASE,
            )
            if inline_exp_match:
                min_years = _extract_minimum_years(cleaned)
                norm_exp = " ".join(re.findall(r"[a-z0-9]+", cleaned.casefold()))
                if norm_exp and norm_exp not in seen:
                    seen.add(norm_exp)
                    candidates.append(
                        JDRequirement(
                            requirement_id=f"req-{len(candidates) + 1}",
                            text=cleaned,
                            category="experience",
                            weight=weights.mandatory,
                            priority="mandatory",
                            source_text=raw_line,
                            minimum_years=min_years,
                        )
                    )
                continue

            # Split regular requirements (by sentence / semicolon)
            for req_text in _split_requirement_text(cleaned):
                normalized = " ".join(re.findall(r"[a-z0-9]+", req_text.casefold()))
                if not normalized or normalized in seen:
                    continue

                category = heading_category or _classify_category(req_text, None)
                if _extract_minimum_years(req_text) is not None:
                    category = "experience"

                if category == "education":
                    excluded_education_count += 1
                    continue

                seen.add(normalized)
                priority = _classify_priority(req_text, heading_priority)
                weight = getattr(weights, priority)

                candidates.append(
                    JDRequirement(
                        requirement_id=f"req-{len(candidates) + 1}",
                        text=req_text,
                        category=category,
                        weight=weight,
                        priority=priority,
                        source_text=source_text,
                        minimum_years=_extract_minimum_years(req_text),
                    )
                )

    warnings = list(extraction_warnings or [])
    if excluded_education_count:
        warnings.append(
            f"Excluded {excluded_education_count} education requirement(s) from scoring."
        )

    jd_obj = JobDescription(
        original_text=original_text or "User-provided requirements",
        requirements=candidates,
        extraction_warnings=warnings,
    )

    if must_have_skills or good_to_have_skills:
        jd_obj = append_explicit_skills(
            jd_obj,
            must_have_skills=must_have_skills,
            good_to_have_skills=good_to_have_skills,
            weights=weights,
        )

    if not jd_obj.requirements:
        if excluded_education_count:
            raise ValueError(
                "The job description contains no scorable requirements after "
                "excluding education requirements."
            )
        raise ValueError("No requirements could be extracted from the job description or skill inputs.")

    return jd_obj


def parse_job_description_file(
    file_path: Path,
    weights: RequirementWeights | None = None,
) -> JobDescription:
    """Read a supported JD document using the existing converter."""
    text, warnings = convert_to_markdown(file_path)
    return parse_job_description(text, weights, warnings)
