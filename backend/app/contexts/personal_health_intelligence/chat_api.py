"""Conversation & Multi-Turn Assistant API routes within Personal Health Intelligence Context."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.contexts.identity_access.service import get_current_user
from app.contexts.personal_health_intelligence.chat_service import ChatService
from app.db import User, get_db
from app.schemas.common import PaginatedResponse
from app.schemas.rag_plan import (
    ChatMessageDTO,
    ChatMessageRequest,
    ChatTurnResponse,
    ConversationCreateRequest,
    ConversationDTO,
)

router = APIRouter(tags=["Conversational AI Context"])


@router.post("/conversations", response_model=ConversationDTO, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreateRequest = ConversationCreateRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ChatService(db).create_conversation(current_user.id, body.title)


@router.get("/conversations", response_model=PaginatedResponse[ConversationDTO])
def list_conversations(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = ChatService(db).list_conversations(current_user.id, limit, offset)
    return PaginatedResponse(items=items, total=total)


@router.get("/conversations/{id}/messages", response_model=PaginatedResponse[ChatMessageDTO])
def get_conversation_messages(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = ChatService(db).list_messages(current_user.id, id)
    if items is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    return PaginatedResponse(items=items, total=len(items))


@router.post("/conversations/{id}/messages", response_model=ChatTurnResponse)
async def send_conversation_message(
    id: str,
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = await ChatService(db).send_message(current_user.id, id, body.message)
    if res is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    return res


@router.delete("/conversations/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = ChatService(db).delete_conversation(current_user.id, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

