"""
Lead scoring formula for INGOT Scout agent.

WEIGHTS ARE INTENTIONALLY VISIBLE AND TUNABLE.
Edit ScoringWeights or pass a custom instance to score_lead().
Decision rationale documented in .planning/phases/02-core-pipeline-scout-through-writer/02-CONTEXT.md.

Scoring formula (from 02-CONTEXT.md locked decisions):
  - stack_domain_match: ~40% — primary signal; tech terms in description vs. user skills
  - company_stage:       ~25% — seed/Series A preferred for outsized early-hire impact
  - job_keyword_match:   ~20% — intent signal when isHiring=True + skill keywords present
  - semantic_similarity: ~15% — TF-IDF cosine(long_description, resume_text) catches gaps

PITFALL: yc-oss `tags` field contains category tags (B2B, SaaS, Developer Tools),
NOT technology names. Use one_liner + long_description free text for stack_domain_match.
"""
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


@dataclass
class ScoringWeights:
    """
    Weighted lead scoring formula.
    Sum must equal 1.0. Edit here or pass custom instance to score_lead().

    Tune by modifying these values. Document your change rationale in comments.
    """
    stack_domain_match: float = 0.40
    company_stage: float = 0.25
    job_keyword_match: float = 0.20
    semantic_similarity: float = 0.15

    def __post_init__(self):
        total = self.stack_domain_match + self.company_stage + self.job_keyword_match + self.semantic_similarity
        assert abs(total - 1.0) < 0.001, f"ScoringWeights must sum to 1.0, got {total}"


DEFAULT_WEIGHTS = ScoringWeights()

# Stage preference scores (seed/Series A = high impact potential)
_STAGE_SCORES: dict[str, float] = {
    "seed": 1.0,
    "series a": 1.0,
    "pre-seed": 0.9,
    "series b": 0.7,
    "series c": 0.5,
    "series d": 0.4,
    "series e": 0.3,
    "public": 0.2,
    "acquired": 0.1,
}


def _extract_tech_terms(text: str) -> set[str]:
    """
    Extract technology-like terms from free text.
    Matches: capitalized acronyms (API, SDK), CamelCase (TypeScript), version strings (Python3),
    and common technology terms. NOT soft skills.
    """
    # Match tech-like tokens: 2+ char sequences, camelCase, all-caps acronyms, versioned terms
    tokens = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b|\b[A-Z]{2,}\b|\b[a-z]+\d+\b', text)
    return {t.lower() for t in tokens if len(t) >= 2}


def _stack_domain_score(company: dict, user_skills: list[str]) -> float:
    """
    Score based on tech term overlap between company description and user skills.
    Checks one_liner + long_description text (NOT tags — those are domain categories).
    """
    company_text = f"{company.get('one_liner', '')} {company.get('long_description', '')}"
    company_terms = _extract_tech_terms(company_text)

    # Also include tag-based domain match (developer tools, infrastructure = +boost)
    high_value_tags = {"developer tools", "infrastructure", "devtools", "dev tools", "b2b"}
    tag_bonus = 0.1 if any(t.lower() in high_value_tags for t in company.get("tags", [])) else 0.0

    if not user_skills or not company_terms:
        return tag_bonus

    skill_terms = {s.lower() for s in user_skills}
    overlap = len(company_terms & skill_terms)
    union = len(company_terms | skill_terms)
    jaccard = overlap / union if union > 0 else 0.0
    return min(1.0, jaccard * 3.0 + tag_bonus)  # scale up; jaccard is typically small


def _stage_score(company: dict) -> float:
    """Score based on company funding stage. Seed/Series A preferred."""
    stage = company.get("stage", "").lower().strip()
    # Try exact match first, then substring match
    if stage in _STAGE_SCORES:
        return _STAGE_SCORES[stage]
    for key, val in _STAGE_SCORES.items():
        if key in stage:
            return val
    # Default: batch-based estimation (older = more mature = lower impact potential)
    batch = company.get("batch", "")
    if batch:
        try:
            year = int(batch[-2:]) + 2000
            if year >= 2023:
                return 0.7  # Recent batch = likely early stage
            elif year >= 2020:
                return 0.5
            else:
                return 0.3
        except (ValueError, IndexError):
            pass
    return 0.3


def _job_keyword_score(company: dict, user_skills: list[str]) -> float:
    """
    Score based on hiring signal + keyword match.
    isHiring=True with overlapping skills in one_liner = strong intent signal.
    """
    is_hiring = company.get("isHiring", False)
    one_liner = company.get("one_liner", "").lower()
    skill_hits = sum(1 for s in user_skills if s.lower() in one_liner)

    base = 0.5 if is_hiring else 0.0
    skill_boost = min(0.5, skill_hits * 0.15)
    return min(1.0, base + skill_boost)


def _semantic_score(company: dict, resume_text: str) -> float:
    """
    TF-IDF cosine similarity between company long_description and user resume.
    Catches semantic overlap missed by keyword matching.
    Returns 0.0 if either text is empty.
    """
    company_desc = company.get("long_description", "") or company.get("one_liner", "")
    if not company_desc or not resume_text:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
        tfidf_matrix = vectorizer.fit_transform([company_desc, resume_text])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(min(1.0, score))
    except Exception:
        return 0.0


def score_lead(
    company: dict,
    user_skills: list[str],
    resume_text: str = "",
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> float:
    """
    Score a YC company against user skills. Returns float 0.0-1.0.

    Weights are documented in ScoringWeights docstring.
    To tune: pass a custom ScoringWeights instance.
    """
    stack = _stack_domain_score(company, user_skills)
    stage = _stage_score(company)
    keyword = _job_keyword_score(company, user_skills)
    semantic = _semantic_score(company, resume_text)

    return (
        weights.stack_domain_match * stack
        + weights.company_stage * stage
        + weights.job_keyword_match * keyword
        + weights.semantic_similarity * semantic
    )
