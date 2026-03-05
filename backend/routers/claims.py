"""Recommended claims endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db, Session, Message, Claim
from schemas import ClaimOut
from services import recommend_claims_by_keywords

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/claims/recommended")
def recommended_claims(session_id: str, db: DBSession = Depends(get_db)):
    """Return recommended claims by keyword/category match from SQLite. No embeddings."""
    logger.info("[claims] Fetching recommended claims for session_id=%s", session_id)
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        logger.warning("[claims] Session not found: %s", session_id)
        raise HTTPException(404, "Session not found")

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.role == "user")
        .all()
    )
    query_text = " ".join(m.content for m in messages).strip()
    if not query_text or len(query_text) < 3:
        query_text = "FRUZAQLA efficacy safety dosing indication mechanism"

    all_claims = db.query(Claim).filter(Claim.compliance_status == "approved").all()
    ordered = recommend_claims_by_keywords(query_text, all_claims, n=20)

    categories = {}
    for c in ordered:
        categories[c.category] = categories.get(c.category, 0) + 1
    logger.info(
        "[claims] Returning %d claims via keyword match, categories: %s",
        len(ordered), categories,
    )

    return {
        "claims": [
            ClaimOut(
                id=c.id,
                text=c.text,
                citation=c.citation,
                source=c.source,
                category=c.category,
                compliance_status=c.compliance_status,
                approved_date=c.approved_date,
            )
            for c in ordered
        ]
    }
