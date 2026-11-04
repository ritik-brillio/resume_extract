from pydantic import BaseModel

from .jd_parser import JobDescription
from .matching_engine import CandidateScore, RequirementScore, ScoringConfiguration

_CATEGORY_ORDER = ("experience", "skills")


class CategoryScore(BaseModel):
    category: str
    score_percentage: float
    requirement_count: int


class RankedCandidateReport(BaseModel):
    rank: int
    source_filename: str
    overall_score: float
    category_scores: list[CategoryScore]
    requirement_scores: list[RequirementScore]
    matched_requirements: list[str]
    partial_or_uncertain_requirements: list[str]
    no_evidence_requirements: list[str]
    extraction_warnings: list[str]


class ScoringReport(BaseModel):
    requirement_count: int
    job_description_source: str | None
    job_description_text: str
    candidates: list[RankedCandidateReport]


def _markdown_text(text: str) -> str:
    return text.replace("\ufffd", "-").replace("|", "\\|")


def _category_label(category: str) -> str:
    return category.title()


def _match_badge(score: float) -> str:
    if score >= 70.0:
        return "Strong Match"
    elif score >= 45.0:
        return "Moderate Match"
    else:
        return "Low Match"


def _effective_weights_for_display(
    requirements: list[RequirementScore],
) -> dict[str, float]:
    has_explicit_priority = any(
        item.priority in {"mandatory", "preferred"} for item in requirements
    )
    if not has_explicit_priority:
        return {item.requirement_id: 1.0 for item in requirements}
    return {item.requirement_id: item.weight for item in requirements}


def build_scoring_report(
    job_description: JobDescription,
    candidates: list[CandidateScore],
    config: ScoringConfiguration,
    job_description_source: str | None = None,
) -> ScoringReport:
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.overall_score,
            candidate.source_filename.casefold(),
        ),
    )
    candidate_reports: list[RankedCandidateReport] = []
    for index, candidate in enumerate(ranked, start=1):
        category_groups: dict[str, list[RequirementScore]] = {}
        for requirement in candidate.requirement_scores:
            category_groups.setdefault(requirement.category, []).append(requirement)

        category_scores = []
        for category in _CATEGORY_ORDER:
            requirements = category_groups.get(category, [])
            eff_weights = _effective_weights_for_display(requirements)
            total_weight = sum(eff_weights.values())
            score_percentage = (
                sum(
                    item.match_score * eff_weights[item.requirement_id]
                    for item in requirements
                )
                / total_weight
                if total_weight
                else 0.0
            )
            category_scores.append(
                CategoryScore(
                    category=category,
                    score_percentage=round(score_percentage, 2),
                    requirement_count=len(requirements),
                )
            )

        candidate_reports.append(
            RankedCandidateReport(
                rank=index,
                source_filename=candidate.source_filename,
                overall_score=candidate.overall_score,
                category_scores=category_scores,
                requirement_scores=candidate.requirement_scores,
                matched_requirements=candidate.matched_requirements,
                partial_or_uncertain_requirements=candidate.partial_or_uncertain_requirements,
                no_evidence_requirements=candidate.no_evidence_requirements,
                extraction_warnings=candidate.extraction_warnings,
            )
        )

    return ScoringReport(
        requirement_count=len(job_description.requirements),
        job_description_source=job_description_source,
        job_description_text=job_description.original_text,
        candidates=candidate_reports,
    )


def render_scoring_report(report: ScoringReport) -> str:
    """Render a clean, minimal, executive report: only scores, matched skills, and unmatched skills."""
    lines = [
        "# Candidate Evaluation Summary",
        "",
        "## Overall Rankings",
        "",
        "| Rank | Candidate | Overall Score | Status | Experience | Skills |",
        "| ---: | --- | ---: | --- | ---: | ---: |",
    ]

    for candidate in report.candidates:
        cat_map = {item.category: item.score_percentage for item in candidate.category_scores}
        exp_score = f"{cat_map.get('experience', 0.0):.1f}%"
        skills_score = f"{cat_map.get('skills', 0.0):.1f}%"
        lines.append(
            f"| {candidate.rank} | **{candidate.source_filename}** | "
            f"**{candidate.overall_score:.1f}%** | {_match_badge(candidate.overall_score)} | "
            f"{exp_score} | {skills_score} |"
        )
    lines.append("")

    for candidate in report.candidates:
        lines.append("---")
        lines.append("")
        cat_map = {item.category: item.score_percentage for item in candidate.category_scores}
        exp_score = f"{cat_map.get('experience', 0.0):.1f}%"
        skills_score = f"{cat_map.get('skills', 0.0):.1f}%"

        lines.append(f"## {candidate.rank}. {candidate.source_filename} - `{candidate.overall_score:.1f}%`")
        lines.append(f"**Experience Score:** {exp_score}  |  **Skills Score:** {skills_score}")
        lines.append("")

        # Matched Skills (score >= 40%)
        matched = [
            item for item in candidate.requirement_scores
            if item.match_score >= 40.0
        ]
        matched.sort(key=lambda x: -x.match_score)

        lines.append("### Matched Skills")
        lines.append("")
        if matched:
            lines.append("| Skill / Requirement | Score |")
            lines.append("|---|---:|")
            for item in matched:
                req_text = _markdown_text(item.requirement.strip())
                lines.append(f"| {req_text} | **{item.match_score:.1f}%** |")
        else:
            lines.append("*No requirements matched above 40%.*")
        lines.append("")

        # Unmatched Skills (missing or score < 40%)
        unmatched = [
            item for item in candidate.requirement_scores
            if item.match_score < 40.0
        ]
        unmatched.sort(key=lambda x: x.match_score)

        lines.append("### Unmatched Skills")
        lines.append("")
        if unmatched:
            lines.append("| Missing Skill / Requirement | Missing Keywords |")
            lines.append("|---|---|")
            for item in unmatched:
                req_text = _markdown_text(item.requirement.strip())
                kw = ", ".join(item.missing_gaps[:6]) if item.missing_gaps else "Not found in resume"
                lines.append(f"| {req_text} | {kw} |")
        else:
            lines.append("*None - all requirements matched.*")
        lines.append("")

    return "\n".join(lines)
