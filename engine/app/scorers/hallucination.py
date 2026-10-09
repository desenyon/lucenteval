"""Hallucination scorer: claim extraction + grounding check against fact corpus."""

import re
from typing import Any

# Simplified fact corpus (would be Wikipedia snapshots + curated facts in production)
KNOWN_FACTS = {
    # Scientific facts
    "the speed of light is approximately 299,792,458 meters per second",
    "water boils at 100 degrees celsius at sea level",
    "the earth orbits the sun",
    "dna is made of four bases: adenine, thymine, guanine, and cytosine",
    "the mitochondria is the powerhouse of the cell",
    # Historical facts
    "world war ii ended in 1945",
    "the united states declared independence in 1776",
    "neil armstrong was the first human to walk on the moon",
    # Math/CS
    "python is a programming language",
    "http stands for hypertext transfer protocol",
    "sql is a query language for relational databases",
    "the binary representation of 10 is 1010",
    # Geographic
    "paris is the capital of france",
    "mount everest is the tallest mountain on earth",
    "the amazon is the largest river by discharge",
    "the pacific ocean is the largest ocean",
    # Numbers
    "pi is approximately 3.14159",
    "there are 7 days in a week",
    "there are 365 days in a year",
    "a hexadecimal digit can represent 4 bits",
}

# Temporal claim patterns — excluded from scoring
TEMPORAL_PATTERNS = [
    r"(?i)(as of|currently|today|now|recent|latest|this year|last year|\d{4})",
    r"(?i)(president|prime minister|ceo|leader|head of)",
    r"(?i)(price|cost|value) (is|was|are)",
    r"(?i)(version \d|v\d+\.\d+)",
]


def _is_temporal(claim: str) -> bool:
    return any(re.search(p, claim) for p in TEMPORAL_PATTERNS)


def _extract_claims(text: str) -> list[dict[str, Any]]:
    """Heuristic claim extractor: splits on sentence boundaries, filters declarative sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    claims = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20:
            continue
        # Skip questions, instructions, opinions with hedging
        if sent.endswith("?"):
            continue
        if re.search(r"(?i)^(please|let me|i think|i believe|maybe|perhaps|could)", sent):
            continue
        claims.append(
            {
                "text": sent,
                "is_temporal": _is_temporal(sent),
            }
        )
    return claims


def _ground_claim(claim_text: str) -> bool:
    """Check claim against fact corpus (simplified substring matching)."""
    # Conservative exact normalized fact matching: overlap alone accepted contradictions
    # such as "Paris is NOT the capital of France" as grounded.
    normalized = " ".join(re.findall(r"\w+", claim_text.lower()))
    return any(normalized == " ".join(re.findall(r"\w+", fact)) for fact in KNOWN_FACTS)


class HallucinationScorer:
    """
    Score = grounded_claims / total_non_temporal_claims
    If no scorable claims: score = 1.0 (benefit of the doubt)
    """

    def score(self, response_text: str) -> dict[str, Any]:
        all_claims = _extract_claims(response_text)
        scorable = [c for c in all_claims if not c["is_temporal"]]
        temporal = [c for c in all_claims if c["is_temporal"]]

        if not scorable:
            return {
                "score": 1.0,
                "total_claims": 0,
                "grounded_claims": 0,
                "temporal_claims": len(temporal),
                "claims": [],
                "rationale": "No scorable factual claims detected",
            }

        grounded = []
        ungrounded = []
        for claim in scorable:
            is_grounded = _ground_claim(claim["text"])
            entry = {**claim, "grounded": is_grounded}
            if is_grounded:
                grounded.append(entry)
            else:
                ungrounded.append(entry)

        # Score is proportion of grounded claims
        # Unverifiable claims (not in our corpus) count as neutral (0.5 weight)
        grounded_count = len(grounded)
        total = len(scorable)

        # Apply conservative scoring: unverifiable → partial credit (0.5)
        unverifiable_partial = 0.5 * len(ungrounded)
        score = (grounded_count + unverifiable_partial) / total if total > 0 else 1.0
        score = round(min(1.0, max(0.0, score)), 4)

        return {
            "score": score,
            "total_claims": total,
            "grounded_claims": grounded_count,
            "ungrounded_claims": len(ungrounded),
            "temporal_claims": len(temporal),
            "claims": (grounded + ungrounded)[:20],
            "rationale": f"{grounded_count}/{total} claims grounded; {len(temporal)} temporal claims excluded",
        }
