"""Session create and get."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db, Session, new_uuid
from schemas import SessionCreate, SessionResp

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/session", response_model=SessionResp)
def create_session(body: SessionCreate, db: DBSession = Depends(get_db)):
    logger.info(
        "[session:create] content_type=%s, audience=%s, campaign_goal=%s, tone=%s",
        body.content_type, body.audience, body.campaign_goal, body.tone,
    )
    sess = Session(
        id=new_uuid(),
        content_type=body.content_type,
        audience=body.audience,
        campaign_goal=body.campaign_goal,
        tone=body.tone,
    )
    db.add(sess)
    db.commit()
    logger.info("[session:create] Created session_id=%s", sess.id)
    return SessionResp(
        session_id=sess.id,
        content_type=sess.content_type,
        audience=sess.audience,
        campaign_goal=sess.campaign_goal,
        tone=sess.tone,
    )


@router.get("/session/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    logger.info("[session:get] Fetching session_id=%s", session_id)
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        logger.warning("[session:get] Session not found: %s", session_id)
        raise HTTPException(404, "Session not found")
    logger.info(
        "[session:get] Found — type=%s, audience=%s, goal=%s, tone=%s",
        sess.content_type, sess.audience, sess.campaign_goal, sess.tone,
    )
    return SessionResp(
        session_id=sess.id,
        content_type=sess.content_type,
        audience=sess.audience or "hcp",
        campaign_goal=sess.campaign_goal or "awareness",
        tone=sess.tone or "clinical",
    )
