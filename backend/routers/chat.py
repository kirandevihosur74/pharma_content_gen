"""Chat and chat stream endpoints."""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from database import get_db, Session, Message, new_uuid
from schemas import ChatReq, ChatResp
import llm

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResp)
def chat(body: ChatReq, db: DBSession = Depends(get_db)):
    logger.info(
        "[chat] session_id=%s, user_content='%s' (%d chars)",
        body.session_id, body.content[:80], len(body.content),
    )
    sess = db.query(Session).filter(Session.id == body.session_id).first()
    if not sess:
        logger.warning("[chat] Session not found: %s", body.session_id)
        raise HTTPException(404, "Session not found")

    user_msg = Message(
        id=new_uuid(),
        session_id=body.session_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    db.flush()
    logger.info("[chat] Saved user message id=%s", user_msg.id)

    all_messages = (
        db.query(Message)
        .filter(Message.session_id == body.session_id)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in all_messages]
    logger.info("[chat] Conversation history: %d messages total", len(history))

    session_context = {
        "content_type": sess.content_type,
        "audience": sess.audience or "hcp",
        "campaign_goal": sess.campaign_goal or "awareness",
        "tone": sess.tone or "clinical",
    }

    t0 = time.perf_counter()
    assistant_text = llm.chat_reply(history, session_context)
    llm_ms = (time.perf_counter() - t0) * 1000
    logger.info("[chat] LLM reply received in %.1fms — %d chars", llm_ms, len(assistant_text))

    assistant_msg = Message(
        id=new_uuid(),
        session_id=body.session_id,
        role="assistant",
        content=assistant_text,
    )
    db.add(assistant_msg)
    db.commit()
    logger.info("[chat] Saved assistant message id=%s, reply_preview='%s'", assistant_msg.id, assistant_text[:100])

    return ChatResp(assistant_message=assistant_text)


@router.post("/chat/stream")
def chat_stream(body: ChatReq, db: DBSession = Depends(get_db)):
    """Stream assistant reply via Server-Sent Events."""
    logger.info("[chat_stream] session_id=%s, content='%s'", body.session_id, body.content[:80])
    sess = db.query(Session).filter(Session.id == body.session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")

    user_msg = Message(id=new_uuid(), session_id=body.session_id, role="user", content=body.content)
    db.add(user_msg)
    db.flush()

    all_messages = (
        db.query(Message)
        .filter(Message.session_id == body.session_id)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in all_messages]

    session_context = {
        "content_type": sess.content_type,
        "audience": sess.audience or "hcp",
        "campaign_goal": sess.campaign_goal or "awareness",
        "tone": sess.tone or "clinical",
    }

    token_stream = llm.chat_reply_stream(history, session_context)
    collected_text = []

    def _llm_sse():
        try:
            for token in token_stream:
                collected_text.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            logger.error("[chat_stream] Stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            full_text = "".join(collected_text)
            if full_text:
                assistant_msg = Message(
                    id=new_uuid(), session_id=body.session_id, role="assistant", content=full_text,
                )
                db.add(assistant_msg)
                db.commit()
                logger.info("[chat_stream] Saved streamed message — %d chars", len(full_text))
            yield f"data: {json.dumps({'done': True, 'full_text': full_text})}\n\n"

    return StreamingResponse(_llm_sse(), media_type="text/event-stream")
