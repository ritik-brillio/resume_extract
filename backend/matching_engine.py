from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, Field, model_validator

from .jd_parser import JDRequirement
from .resume_chunker import ResumeChunk

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class ScoringConfiguration(BaseModel):
    mandatory_weight: float = Field(default=3.0, gt=0)
    preferred_weight: float = Field(default=1.0, gt=0)
    unspecified_weight: float = Field(default=2.0, gt=0)
    experience_category_weight: float = Field(
        default=0.55, ge=0, le=1
    )
    skills_category_weight: float = Field(
        default=0.40, ge=0, le=1
    )
    summary_category_weight: float = Field(
        default=0.05, ge=0, le=1
    )
    semantic_similarity_threshold: float = Field(default=0.35, ge=0, le=1)
    depth_score_weight: float = Field(default=0.2, ge=0, le=1)
    recency_score_weight: float = Field(default=0.1, ge=0, le=1)
    experience_score_weight: float = Field(default=0.7, ge=0, le=1)
    strong_match_threshold: float = Field(default=0.75, gt=0, le=1)
    partial_match_threshold: float = Field(default=0.25, gt=0, le=1)
    max_evidence: int = Field(default=3, ge=1)
    max_chunk_words: int = Field(default=120, ge=1)
    chunk_overlap_words: int = Field(default=0, ge=0)

    @model_validator(mode="before")
    @classmethod
    def normalize_category_weights(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        defaults = {
            "experience_category_weight": 0.55,
            "skills_category_weight": 0.40,
            "summary_category_weight": 0.05,
        }
        configured = {
            key: float(values.get(key, default))
            for key, default in defaults.items()
        }
        total = sum(configured.values())
        if total > 0 and not math.isclose(total, 1.0, abs_tol=1e-9):
            values = {
                **values,
                **{key: weight / total for key, weight in configured.items()},
            }
        return values

    @model_validator(mode="after")
    def validate_match_thresholds(self) -> "ScoringConfiguration":
        if self.partial_match_threshold >= self.strong_match_threshold:
            raise ValueError(
                "partial_match_threshold must be less than "
                "strong_match_threshold."
            )
        category_weights = (
            self.experience_category_weight,
            self.skills_category_weight,
            self.summary_category_weight,
        )
        if not math.isclose(sum(category_weights), 1.0, abs_tol=1e-9):
            raise ValueError(
                "Experience, skills, and summary category weights must sum to 1."
            )
        if self.depth_score_weight + self.recency_score_weight >= 1:
            raise ValueError(
                "depth_score_weight and recency_score_weight must sum to "
                "less than 1."
            )
        return self


class EvidenceExcerpt(BaseModel):
    chunk_id: str
    source_section: str
    company_name: str | None
    date_range: str | None
    text: str
    retrieval_score: float
    matched_terms: list[str]
    lexical_score: float
    semantic_score: float
    depth_score: float
    recency_score: float


class RequirementScore(BaseModel):
    requirement_id: str
    requirement: str
    category: str
    weight: float
    priority: str
    minimum_years: float | None
    candidate_experience_years: float | None
    relevant_experience_years: float | None
    match_score: float = Field(ge=0, le=100)
    match_status: str
    supporting_evidence: list[EvidenceExcerpt]
    source_sections: list[str]
    missing_gaps: list[str]
    uncertainties: list[str]
    explanation: str


class CandidateScore(BaseModel):
    source_filename: str
    overall_score: float = Field(ge=0, le=100)
    total_experience_years: float | None = None
    requirement_scores: list[RequirementScore]
    matched_requirements: list[str]
    partial_or_uncertain_requirements: list[str]
    no_evidence_requirements: list[str]
    extraction_warnings: list[str]


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[+#.]+|/[a-z0-9]+)*", re.IGNORECASE)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "have", "in", "into", "is", "it", "of", "on", "or", "that", "the",
    "their", "to", "with", "will", "you", "your",
    "must", "required", "mandatory", "essential", "minimum", "preferred",
    "preferably", "least", "using", "hands", "experience", "knowledge",
    "understanding", "familiarity", "strong", "good", "perform", "build",
    "develop", "maintain", "maintaining", "similar", "etc", "e.g", "i.e",
    "across", "including", "covering", "work", "working", "responsibilities",
    "duties", "relevant",
}
_MONTHS = {
    name.casefold(): index
    for index, name in enumerate(
        (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November",
            "December",
        ),
        start=1,
    )
}
_DATE_ENDPOINT_PATTERN = re.compile(
    r"(?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+)?((?:19|20)\d{2})|"
    r"\b(present|current)\b",
    re.IGNORECASE,
)
_RELEVANT_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:qa|quality assurance|testing|test automation|test engineer)\b",
    re.IGNORECASE,
)
_TESTING_REQUIREMENT_PATTERN = re.compile(
    r"\b(?:qa|quality assurance|test(?:ing)?|software quality)\b",
    re.IGNORECASE,
)
SEMANTIC_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _embedding_model() -> SentenceTransformer:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Semantic scoring requires sentence-transformers. Install the "
            "project dependencies with 'pip install -r requirements.txt'."
        ) from exc
    try:
        return SentenceTransformer(SEMANTIC_MODEL_NAME, local_files_only=True)
    except Exception:
        return SentenceTransformer(SEMANTIC_MODEL_NAME)


def _encode_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    model = _embedding_model()
    return model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def _semantic_similarities(
    requirement_embedding: np.ndarray,
    chunk_embeddings: np.ndarray,
) -> list[float]:
    if not len(chunk_embeddings):
        return []
    return [
        max(-1.0, min(1.0, float(similarity)))
        for similarity in chunk_embeddings @ requirement_embedding
    ]


def _semantic_relevance(similarity: float, threshold: float) -> float:
    return max(0.0, min(1.0, (similarity - threshold) / (1 - threshold)))


def _hybrid_weights(category: str) -> tuple[float, float]:
    if category == "skills":
        return 0.75, 0.25
    return 0.20, 0.80


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_PATTERN.findall(text)]


def _query_terms(text: str) -> set[str]:
    return {token for token in _tokens(text) if token not in _STOP_WORDS}


def _bm25_scores(
    query_terms: set[str],
    chunks: list[ResumeChunk],
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    if not chunks or not query_terms:
        return [0.0] * len(chunks)

    documents = [
        [token for token in _tokens(chunk.text) if token not in _STOP_WORDS]
        for chunk in chunks
    ]
    document_frequencies: Counter[str] = Counter()
    for terms in documents:
        document_frequencies.update(set(terms))

    average_length = sum(map(len, documents)) / len(documents) or 1.0
    scores: list[float] = []
    for document in documents:
        frequencies = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            doc_frequency = document_frequencies[term]
            inverse_frequency = math.log(
                1
                + (len(documents) - doc_frequency + 0.5)
                / (doc_frequency + 0.5)
            )
            denominator = frequency + k1 * (
                1 - b + b * len(document) / average_length
            )
            score += (
                inverse_frequency
                * frequency
                * (k1 + 1)
                / denominator
            )
        scores.append(score)
    return scores


def _depth_score(section: str) -> float:
    return {
        "experience": 1.0,
        "projects": 0.95,
        "research": 0.85,
        "skills": 0.85,
        "certifications": 0.80,
        "summary": 0.70,
        "education": 0.65,
        "other": 0.50,
    }.get(section, 0.50)


def _calibrate_match(raw: float) -> float:
    """Map raw lexical+semantic blend onto an ATS-aligned evaluation curve."""
    if raw <= 0.05:
        return 0.0
    calibrated = 1.0 / (1.0 + math.exp(-8.0 * (raw - 0.32)))
    return min(1.0, max(0.0, calibrated))


def _recency_score(date_range: str | None) -> float:
    if not date_range:
        return 0.5
    if re.search(r"\b(?:present|current)\b", date_range, re.IGNORECASE):
        return 1.0
    years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", date_range)]
    if not years:
        return 0.5
    age = max(0, date.today().year - max(years))
    return max(0.3, 1.0 - age * 0.07)


def _date_range_months(date_range: str) -> tuple[int, int] | None:
    endpoints: list[int] = []
    for match in _DATE_ENDPOINT_PATTERN.finditer(date_range):
        month_name, year_text, current = match.groups()
        if current:
            endpoints.append(date.today().year * 12 + date.today().month)
        elif year_text:
            month = 1
            if month_name:
                month = next(
                    number
                    for name, number in _MONTHS.items()
                    if name.startswith(month_name.casefold()[:3])
                )
            endpoints.append(int(year_text) * 12 + month)
    if len(endpoints) < 2:
        return None
    start, end = endpoints[0], endpoints[-1]
    return (start, max(start, end))


def _domain_pattern_for_requirement(requirement_text: str) -> re.Pattern[str] | None:
    lowered = requirement_text.casefold()
    if re.search(r"\b(?:qa|quality assurance|testing|test automation|sdet|tester|eval(?:s|uation)?)\b", lowered):
        return re.compile(
            r"\b(?:qa|quality assurance|testing|test automation|test engineer|sdet|test lead|tester|qa engineer|test cases|pytest)\b",
            re.IGNORECASE,
        )
    if re.search(r"\b(?:frontend|front-end|ui\b|user interface|react|angular|vue|next\.?js)\b", lowered) and not re.search(r"\bfull[\s-]?stack\b", lowered):
        return re.compile(
            r"\b(?:frontend|front-end|ui\b|react|angular|vue|next\.?js|web developer|javascript developer|frontend engineer|ui engineer|client-side)\b",
            re.IGNORECASE,
        )
    if re.search(r"\bfull[\s-]?stack\b", lowered):
        return re.compile(
            r"\b(?:full[\s-]?stack|software engineer|software developer|web developer|full stack developer|application developer|product engineer)\b",
            re.IGNORECASE,
        )
    if re.search(r"\b(?:backend|back-end|api|server|microservices|distributed systems)\b", lowered):
        return re.compile(
            r"\b(?:backend|back-end|api|server|software engineer|software developer|backend engineer|platform engineer|systems engineer)\b",
            re.IGNORECASE,
        )
    if re.search(r"\b(?:machine learning|deep learning|data scientist|ai engineer|ml engineer|llm|nlp|computer vision)\b", lowered):
        return re.compile(
            r"\b(?:machine learning|deep learning|data scientist|ai engineer|ml engineer|data engineer|nlp|researcher|ai/ml|applied scientist)\b",
            re.IGNORECASE,
        )
    if re.search(r"\b(?:devops|sre|cloud|infrastructure|platform|kubernetes|terraform)\b", lowered):
        return re.compile(
            r"\b(?:devops|sre|cloud engineer|infrastructure|site reliability|platform engineer|cloud architect)\b",
            re.IGNORECASE,
        )
    return None


def _experience_months(
    chunks: list[ResumeChunk],
    domain_pattern: re.Pattern[str] | None = None,
) -> tuple[int, int]:
    dated_roles: dict[tuple[int, int], bool] = {}
    for chunk in chunks:
        if chunk.source_section != "experience" or not chunk.date_range:
            continue
        interval = _date_range_months(chunk.date_range)
        if interval:
            relevant = bool(domain_pattern.search(chunk.text)) if domain_pattern else True
            dated_roles[interval] = dated_roles.get(interval, False) or relevant

    intervals = sorted(dated_roles)
    merged: list[list[int]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    total_months = sum(end - start for start, end in merged)

    relevant_intervals = sorted(
        interval for interval, relevant in dated_roles.items() if relevant
    )
    relevant_months = 0
    merged = []
    for start, end in relevant_intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    relevant_months = sum(end - start for start, end in merged)
    return total_months, relevant_months


def _requirement_experience_months(
    requirement: JDRequirement,
    chunks: list[ResumeChunk],
) -> tuple[int, int]:
    combined_text = f"{requirement.text} {requirement.source_text}"
    domain_pattern = _domain_pattern_for_requirement(combined_text)
    total_months, relevant_months = _experience_months(chunks, domain_pattern)
    return total_months, relevant_months if domain_pattern else total_months


def score_requirement(
    requirement: JDRequirement,
    chunks: list[ResumeChunk],
    config: ScoringConfiguration,
    chunk_embeddings: np.ndarray | None = None,
    requirement_embedding: np.ndarray | None = None,
) -> RequirementScore:
    """Score evidence using the requirement category's lexical/semantic blend."""
    query_terms = _query_terms(requirement.text)
    retrieval_scores = _bm25_scores(query_terms, chunks)
    if chunk_embeddings is None:
        chunk_embeddings = _encode_texts([chunk.text for chunk in chunks])
    if requirement_embedding is None:
        requirement_embedding = _encode_texts([requirement.text])[0]
    semantic_scores = _semantic_similarities(
        requirement_embedding, chunk_embeddings
    )
    lexical_weight, semantic_weight = _hybrid_weights(requirement.category)
    maximum_bm25 = max(retrieval_scores, default=0.0)
    chunk_lexical_scores: list[float] = []
    chunk_semantic_scores: list[float] = []
    chunk_hybrid_scores: list[float] = []
    for index, chunk in enumerate(chunks):
        passage_terms = set(_tokens(chunk.text))
        lexical_coverage = (
            len(query_terms.intersection(passage_terms)) / len(query_terms)
            if query_terms
            else 0.0
        )
        normalized_bm25 = (
            retrieval_scores[index] / maximum_bm25 if maximum_bm25 else 0.0
        )
        lexical_score = (lexical_coverage + normalized_bm25) / 2
        semantic_score = _semantic_relevance(
            semantic_scores[index],
            config.semantic_similarity_threshold,
        )
        chunk_lexical_scores.append(lexical_score)
        chunk_semantic_scores.append(semantic_score)
        chunk_hybrid_scores.append(
            lexical_weight * lexical_score
            + semantic_weight * semantic_score
        )

    ranked_indices = sorted(
        range(len(chunks)),
        key=lambda index: chunk_hybrid_scores[index],
        reverse=True,
    )
    selected_indices = [
        index
        for index in ranked_indices
        if chunk_hybrid_scores[index] > 0
    ][: config.max_evidence]
    if requirement.minimum_years is not None:
        dated_experience_indices = [
            index
            for index, chunk in enumerate(chunks)
            if chunk.source_section == "experience"
            and chunk.date_range
            and (
                not _TESTING_REQUIREMENT_PATTERN.search(requirement.text)
                or _RELEVANT_EXPERIENCE_PATTERN.search(chunk.text)
            )
        ]
        if dated_experience_indices and not any(
            chunks[index].date_range for index in selected_indices
        ):
            if len(selected_indices) >= config.max_evidence:
                selected_indices[-1] = dated_experience_indices[0]
            else:
                selected_indices.append(dated_experience_indices[0])

    matched_terms: set[str] = set()
    evidence: list[EvidenceExcerpt] = []
    evidence_context_scores: list[float] = []
    missing_terms: set[str] = set(query_terms)
    for index in selected_indices:
        chunk = chunks[index]
        passage_terms = set(_tokens(chunk.text))
        passage_matches = query_terms.intersection(passage_terms)
        matched_terms.update(passage_matches)
        missing_terms.difference_update(passage_matches)
        depth = _depth_score(chunk.source_section)
        recency = _recency_score(chunk.date_range)
        evidence_context_scores.append(
            config.depth_score_weight * depth
            + config.recency_score_weight * recency
        )
        evidence.append(
            EvidenceExcerpt(
                chunk_id=chunk.chunk_id,
                source_section=chunk.source_section,
                company_name=chunk.company_name,
                date_range=chunk.date_range,
                text=chunk.text,
                retrieval_score=round(chunk_hybrid_scores[index], 4),
                matched_terms=sorted(passage_matches),
                lexical_score=round(chunk_lexical_scores[index], 4),
                semantic_score=round(chunk_semantic_scores[index], 4),
                depth_score=depth,
                recency_score=round(recency, 4),
            )
        )

    lexical_score = len(matched_terms) / len(query_terms) if query_terms else 0.0
    semantic_score = max(
        (chunk_semantic_scores[index] for index in selected_indices),
        default=0.0,
    )
    hybrid_score = (
        lexical_weight * lexical_score
        + semantic_weight * semantic_score
    )
    if not selected_indices:
        evidence_score = 0.0
    else:
        best_depth = max((item.depth_score for item in evidence), default=0.5)
        best_recency = max((item.recency_score for item in evidence), default=0.5)
        calibrated_hybrid = _calibrate_match(hybrid_score)
        context_multiplier = 0.80 + 0.15 * best_depth + 0.05 * best_recency
        evidence_score = max(0.0, min(1.0, calibrated_hybrid * context_multiplier)) * 100

    candidate_experience_years: float | None = None
    relevant_experience_years: float | None = None
    match_score = evidence_score
    uncertainty_notes: list[str] = []
    if requirement.minimum_years is not None:
        total_months, relevant_months = _requirement_experience_months(
            requirement, chunks
        )
        candidate_experience_years = round(total_months / 12, 2)
        relevant_experience_years = round(relevant_months / 12, 2)
        
        domain_pattern = _domain_pattern_for_requirement(
            f"{requirement.text} {requirement.source_text}"
        )
        years_for_requirement = relevant_months if domain_pattern else total_months
        duration_fraction = min(
            1.0,
            years_for_requirement / (requirement.minimum_years * 12),
        )
        experience_weight = config.experience_score_weight
        match_score = (
            evidence_score * (1 - experience_weight)
            + duration_fraction * 100 * experience_weight
        )
        if not total_months:
            uncertainty_notes.append(
                "No dated work-experience ranges were found in the extracted "
                "experience section, so the years requirement is not verified."
            )
        elif duration_fraction < 1:
            uncertainty_notes.append(
                f"The extracted experience section shows about "
                f"{years_for_requirement / 12:.1f} years against the "
                f"{requirement.minimum_years:g}-year requirement."
            )
        else:
            uncertainty_notes.append(
                f"The dated experience evidence indicates at least "
                f"{requirement.minimum_years:g} years; dates and relevance "
                "should still be verified by a recruiter."
            )
    if not query_terms:
        status = "uncertain"
        explanation = (
            "The requirement has no distinct searchable terms; evidence "
            "cannot be assessed reliably."
        )
    elif match_score == 0:
        status = "no evidence found"
        explanation = (
            "No matching terms were found in the retrieved resume passages. "
            "This is not proof that the candidate lacks the capability."
        )
        evidence = []
    elif match_score / 100 >= config.strong_match_threshold:
        status = "strong evidence"
        explanation = (
            "The requirement is supported by retrieved evidence and, when "
            "a minimum is stated, estimated dated experience. This is not "
            "independent verification."
        )
    elif match_score / 100 >= config.partial_match_threshold:
        status = "partial evidence"
        explanation = (
            "The retrieved evidence supports only part of the requirement or "
            "appears mainly in a lower-depth context."
        )
    else:
        status = "uncertain"
        explanation = (
            "Only a small portion of the requirement terms are present; "
            "manual review is needed."
        )

    return RequirementScore(
        requirement_id=requirement.requirement_id,
        requirement=requirement.text,
        category=requirement.category,
        weight=requirement.weight,
        priority=requirement.priority,
        minimum_years=requirement.minimum_years,
        candidate_experience_years=candidate_experience_years,
        relevant_experience_years=relevant_experience_years,
        match_score=round(match_score, 2),
        match_status=status,
        supporting_evidence=evidence,
        source_sections=list(
            dict.fromkeys(item.source_section for item in evidence)
        ),
        missing_gaps=sorted(missing_terms),
        uncertainties=uncertainty_notes,
        explanation=explanation,
    )


def _effective_weights(
    requirement_scores: list[RequirementScore],
) -> dict[str, float]:
    """Return 1/N equal weights when no explicit priority signals exist; else use stored weights."""
    has_explicit_priority = any(
        item.priority in {"mandatory", "preferred"}
        for item in requirement_scores
    )
    if not has_explicit_priority:
        return {item.requirement_id: 1.0 for item in requirement_scores}
    return {item.requirement_id: item.weight for item in requirement_scores}


def score_candidate(
    source_filename: str,
    requirements: list[JDRequirement],
    chunks: list[ResumeChunk],
    extraction_warnings: list[str],
    config: ScoringConfiguration,
) -> CandidateScore:
    chunks = [
        chunk for chunk in chunks if chunk.source_section != "education"
    ]
    chunk_embeddings = _encode_texts([chunk.text for chunk in chunks])
    requirement_embeddings = _encode_texts(
        [requirement.text for requirement in requirements]
    )
    requirement_scores = [
        score_requirement(
            requirement,
            chunks,
            config,
            chunk_embeddings,
            requirement_embeddings[index],
        )
        for index, requirement in enumerate(requirements)
    ]
    category_weights = {
        "experience": config.experience_category_weight,
        "skills": config.skills_category_weight,
        "summary": config.summary_category_weight,
    }
    category_scores: dict[str, float] = {}
    for category in category_weights:
        category_requirements = [
            item for item in requirement_scores if item.category == category
        ]
        # 1/N fallback: use equal weights when no explicit priority exists in JD
        eff_weights = _effective_weights(category_requirements)
        total_weight = sum(eff_weights.values())
        category_scores[category] = (
            sum(
                item.match_score * eff_weights[item.requirement_id]
                for item in category_requirements
            )
            / total_weight
            if total_weight
            else 0.0
        )
    # 1. Category scores
    active_categories = {
        cat: weight
        for cat, weight in category_weights.items()
        if any(item.category == cat for item in requirement_scores)
    }

    # 2. Applied Justification: check what fraction of skills were demonstrated in actual work/projects
    skill_reqs = [item for item in requirement_scores if item.category == "skills"]
    applied_weight = 0.0
    total_skill_weight = 0.0
    for item in skill_reqs:
        total_skill_weight += item.weight
        has_applied = any(
            ev.source_section in {"experience", "projects"} and ev.retrieval_score >= 0.20
            for ev in item.supporting_evidence
        )
        if has_applied or item.match_score >= 60.0:
            applied_weight += item.weight

    applied_score = (applied_weight / total_skill_weight * 100) if total_skill_weight > 0 else 0.0

    # 3. Years of Experience (YoE) Fit
    total_m, qa_m = _experience_months(chunks)
    is_testing_jd = any(
        _TESTING_REQUIREMENT_PATTERN.search(r.text) for r in requirements
    )
    relevant_years = (qa_m / 12.0) if is_testing_jd else (total_m / 12.0)
    target_years = next(
        (r.minimum_years for r in requirements if r.minimum_years is not None),
        2.0,
    )
    yoe_score = min(1.0, relevant_years / target_years) * 100 if target_years > 0 else 100.0

    # 4. Balanced ATS Recruiter Scoring Model:
    # 45% Skills + 35% Experience + 10% Applied Justification in Projects/Work + 10% YoE Fit
    skills_val = category_scores.get("skills", 0.0)
    exp_val = category_scores.get("experience", 0.0)

    if "skills" in active_categories and "experience" in active_categories:
        overall_score = (
            0.45 * skills_val
            + 0.35 * exp_val
            + 0.10 * applied_score
            + 0.10 * yoe_score
        )
    elif "skills" in active_categories:
        overall_score = 0.70 * skills_val + 0.15 * applied_score + 0.15 * yoe_score
    elif "experience" in active_categories:
        overall_score = 0.80 * exp_val + 0.20 * yoe_score
    else:
        overall_score = sum(category_scores.values()) / (len(category_scores) or 1)

    total_experience_years = round(total_m / 12.0, 1) if total_m > 0 else 0.0

    return CandidateScore(
        source_filename=source_filename,
        overall_score=round(overall_score, 2),
        total_experience_years=total_experience_years,
        requirement_scores=requirement_scores,
        matched_requirements=[
            item.requirement
            for item in requirement_scores
            if item.match_status == "strong evidence"
        ],
        partial_or_uncertain_requirements=[
            item.requirement
            for item in requirement_scores
            if item.match_status in {"partial evidence", "uncertain"}
        ],
        no_evidence_requirements=[
            item.requirement
            for item in requirement_scores
            if item.match_status == "no evidence found"
        ],
        extraction_warnings=extraction_warnings,
    )
