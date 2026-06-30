from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.services.ai_chat_service import generate_chat_response


router = APIRouter(prefix="/ai-chat", tags=["ai-chat"])


class AiChatRequest(BaseModel):
    message: str = Field(..., max_length=1000)
    conversation_id: Optional[str] = None
    page: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Message must not be empty")
        return text


class AiChatResponse(BaseModel):
    answer: str
    conversation_id: str
    suggested_questions: list[str] = Field(default_factory=list)


@router.post("", response_model=AiChatResponse)
def ai_chat(
    payload: AiChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiChatResponse:
    try:
        result = generate_chat_response(
            db=db,
            current_user=current_user,
            message=payload.message,
            conversation_id=payload.conversation_id,
            page=payload.page,
        )
        return AiChatResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Xin lỗi, Trợ lý NutriGain chưa thể trả lời lúc này.",
        ) from exc
