"""Messages list and clear."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db, Session, Message

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/messages")
def get_messages(session_id: str, db: DBSession = Depends(get_db)):
    logger.info("[messages] Fetching messages for session_id=%s", session_id)
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        logger.warning("[messages] Session not found: %s", session_id)
        raise HTTPException(404, "Session not found")

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )
    logger.info("[messages] Returning %d messages", len(messages))
    return {
        "messages": [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
    }


@router.delete("/messages")
def clear_messages(session_id: str, db: DBSession = Depends(get_db)):
    logger.info("[messages:clear] Clearing messages for session_id=%s", session_id)
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")

    count = db.query(Message).filter(Message.session_id == session_id).delete()
    db.commit()
    logger.info("[messages:clear] Deleted %d messages", count)
    return {"deleted": count}
