"""Claim recommendation by keyword/category match."""

from database import Claim

CATEGORY_ORDER = ["indication", "efficacy", "mechanism", "dosing", "quality_of_life", "safety"]
QUERY_TO_CATEGORY = {
    "dosing": "dosing", "dose": "dosing", "oral": "dosing",
    "safety": "safety", "adverse": "safety", "side effect": "safety", "tolerab": "safety",
    "efficacy": "efficacy", "os ": "efficacy", "survival": "efficacy", "fresco": "efficacy", "pfs": "efficacy",
    "mechanism": "mechanism", "moa": "mechanism", "vegf": "mechanism", "angiogenesis": "mechanism",
    "indication": "indication", "mCRC": "indication", "indicated": "indication",
    "quality": "quality_of_life", "qol": "quality_of_life",
}


def recommend_claims_by_keywords(query: str, claims: list[Claim], n: int = 20) -> list[Claim]:
    """Rank claims by keyword match to query. Returns top n, ordered by relevance then category."""
    lower = query.lower()
    matched_cats = {QUERY_TO_CATEGORY[k] for k in QUERY_TO_CATEGORY if k in lower}
    if not matched_cats:
        matched_cats = {"indication", "efficacy", "safety"}

    def score(c: Claim) -> tuple[int, int]:
        cat_match = 2 if c.category in matched_cats else 0
        text_match = 1 if any(w in (c.text or "").lower() for w in lower.split() if len(w) > 3) else 0
        cat_rank = CATEGORY_ORDER.index(c.category) if c.category in CATEGORY_ORDER else 99
        return (-(cat_match + text_match), cat_rank)

    return sorted(claims, key=score)[:n]
