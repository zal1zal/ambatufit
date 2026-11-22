"""Multi-turn Conversational AI Service with user isolation, rolling context & safety gate."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.clients.ai_client import ai_client
from app.db import Assessment, Conversation, ConversationMessage
from app.contexts.personal_health_intelligence.repository import HealthRepository
from app.schemas.rag_plan import (
    ChatCitationDTO,
    ChatMessageDTO,
    ChatTurnResponse,
    ConversationDTO,
)


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clean_title(text: str, max_len: int = 48) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean or "Percakapan Baru"
    cut = clean[:max_len].rsplit(" ", 1)[0].strip()
    return cut or clean[:max_len]


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.health_repo = HealthRepository(db)

    def _conv_dto(self, conv: Conversation) -> ConversationDTO:
        return ConversationDTO(
            id=conv.id,
            title=conv.title,
            active_topic=conv.active_topic,
            summary=conv.summary,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def _msg_dto(self, m: ConversationMessage) -> ChatMessageDTO:
        cits = [ChatCitationDTO(**c) for c in json.loads(m.citations_json or "[]")]
        return ChatMessageDTO(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            intent=m.intent,
            citations=cits,
            safety_alert=bool(m.safety_alert),
            generation_mode=m.generation_mode,
            created_at=m.created_at,
        )

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> ConversationDTO:
        now = _utc_now()
        conv = Conversation(
            id=f"conv-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            title=(title or "").strip() or "Percakapan Baru",
            active_topic=None,
            summary=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return self._conv_dto(conv)

    def list_conversations(self, user_id: str, limit: int = 100, offset: int = 0) -> tuple[List[ConversationDTO], int]:
        q = self.db.query(Conversation).filter(Conversation.user_id == user_id)
        total = q.count()
        rows = q.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()
        return [self._conv_dto(r) for r in rows], total

    def get_owned_conversation(self, user_id: str, conv_id: str) -> Optional[Conversation]:
        conv = self.db.get(Conversation, conv_id)
        if not conv or conv.user_id != user_id:
            return None
        return conv

    def list_messages(self, user_id: str, conv_id: str) -> Optional[List[ChatMessageDTO]]:
        conv = self.get_owned_conversation(user_id, conv_id)
        if not conv:
            return None
        rows = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conv.id, ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            .all()
        )
        return [self._msg_dto(r) for r in rows]

    def delete_conversation(self, user_id: str, conv_id: str) -> bool:
        conv = self.get_owned_conversation(user_id, conv_id)
        if not conv:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True

    async def send_message(self, user_id: str, conv_id: str, content: str) -> Optional[ChatTurnResponse]:
        conv = self.get_owned_conversation(user_id, conv_id)
        if not conv:
            return None

        history_rows = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conv.id, ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            .all()
        )
        history = [{"role": r.role, "content": r.content} for r in history_rows[-8:]]

        profile = self.health_repo.get_or_create_profile(user_id)
        profile_summary = (
            f"goal={profile.health_goal}, dietary={profile.dietary_preferences}, "
            f"activity={profile.activity_preferences}, known={profile.known_conditions}"
        )
        concern = self.db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.safety_level.in_(["urgent", "review_recommended"]),
        ).first()
        safety_level = concern.safety_level if concern else "none"

        user_msg = ConversationMessage(
            id=f"msg-u-{uuid.uuid4().hex[:10]}",
            conversation_id=conv.id,
            user_id=user_id,
            role="user",
            content=content.strip(),
            created_at=_utc_now(),
        )
        self.db.add(user_msg)
        self.db.flush()

        ai_out = await ai_client.chat_turn(
            message=content.strip(),
            history=history,
            active_topic=conv.active_topic,
            summary=conv.summary,
            profile_summary=profile_summary,
            safety_level=safety_level,
        )

        asst_msg = ConversationMessage(
            id=f"msg-a-{uuid.uuid4().hex[:10]}",
            conversation_id=conv.id,
            user_id=user_id,
            role="assistant",
            content=ai_out["reply"],
            intent=ai_out.get("intent"),
            citations_json=json.dumps(ai_out.get("citations") or [], ensure_ascii=False),
            safety_alert=bool(ai_out.get("safety_alert", False)),
            generation_mode=ai_out.get("generation_mode"),
            created_at=_utc_now(),
        )
        self.db.add(asst_msg)

        if ai_out.get("active_topic"):
            conv.active_topic = ai_out["active_topic"][:150]
        if conv.title in ("Percakapan Kesehatan Baru", "Percakapan Baru"):
            conv.title = _clean_title(conv.active_topic or content.strip(), max_len=48)
        if len(history_rows) >= 6:
            conv.summary = (
                f"Topik aktif: {conv.active_topic or '-'}. Pertanyaan terakhir: {content.strip()[:160]}."
            )
        conv.updated_at = _utc_now()

        self.db.commit()
        self.db.refresh(conv)
        self.db.refresh(user_msg)
        self.db.refresh(asst_msg)

        return ChatTurnResponse(
            conversation=self._conv_dto(conv),
            user_message=self._msg_dto(user_msg),
            assistant_message=self._msg_dto(asst_msg),
            evidence_sufficient=bool(ai_out.get("evidence_sufficient", True)),
            clarification_needed=bool(ai_out.get("clarification_needed", False)),
            suggested_entities=list(ai_out.get("suggested_entities") or []),
            llm_provider=str(ai_out.get("llm_provider") or "none"),
            llm_model=ai_out.get("llm_model"),
        )

