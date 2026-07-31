from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_tenant_owner
from app.models.user import User
from app.models.tenant import Tenant
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.whatsapp import WhatsAppConversationDetail, WhatsAppConversationSummary, WhatsAppReplyRequest, WhatsAppReplyResponse, WhatsAppMessageResponse
from app.services.whatsapp_service import send_outbound_message

router = APIRouter(prefix="/dashboard/whatsapp", tags=["whatsapp"])


def conversation_summary_row(conversation: WhatsAppConversation) -> WhatsAppConversationSummary:
    return WhatsAppConversationSummary(
        id=conversation.id,
        tenant_id=conversation.tenant_id,
        customer_phone=conversation.customer_phone,
        customer_name=conversation.customer_name,
        state=conversation.state,
        status=conversation.status,
        summary=conversation.summary,
        last_message_at=conversation.last_message_at,
        last_inbound_at=conversation.last_inbound_at,
        last_outbound_at=conversation.last_outbound_at,
        booking_id=conversation.booking_id,
        assigned_user_id=conversation.assigned_user_id,
    )


def message_row(message: WhatsAppMessage) -> WhatsAppMessageResponse:
    return WhatsAppMessageResponse(
        id=message.id,
        direction=message.direction,
        author_type=message.author_type,
        body=message.body,
        status=message.status,
        provider_message_id=message.provider_message_id,
        sent_at=message.sent_at,
        created_at=message.created_at,
    )


@router.get("/conversations", response_model=list[WhatsAppConversationSummary])
async def list_conversations(
    current_user: Annotated[User, Depends(require_tenant_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = None,
) -> list[WhatsAppConversationSummary]:
    stmt = select(WhatsAppConversation).where(WhatsAppConversation.tenant_id == current_user.tenant_id)
    if status_filter:
        stmt = stmt.where(WhatsAppConversation.status == status_filter)
    stmt = stmt.order_by(WhatsAppConversation.last_message_at.desc().nullslast(), WhatsAppConversation.updated_at.desc())
    result = await db.execute(stmt)
    return [conversation_summary_row(conversation) for conversation in result.scalars().all()]


@router.get("/conversations/{conversation_id}", response_model=WhatsAppConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(require_tenant_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhatsAppConversationDetail:
    result = await db.execute(
        select(WhatsAppConversation).where(
            WhatsAppConversation.tenant_id == current_user.tenant_id,
            WhatsAppConversation.id == conversation_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "CONVERSATION_NOT_FOUND", "message": "Conversation was not found."})
    messages_result = await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conversation.id)
        .order_by(WhatsAppMessage.created_at.asc())
    )
    return WhatsAppConversationDetail(
        **conversation_summary_row(conversation).model_dump(),
        booking_context=conversation.booking_context,
        messages=[message_row(message) for message in messages_result.scalars().all()],
    )


@router.post("/conversations/{conversation_id}/claim", response_model=WhatsAppConversationSummary)
async def claim_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(require_tenant_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhatsAppConversationSummary:
    result = await db.execute(
        select(WhatsAppConversation).where(
            WhatsAppConversation.tenant_id == current_user.tenant_id,
            WhatsAppConversation.id == conversation_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "CONVERSATION_NOT_FOUND", "message": "Conversation was not found."})
    conversation.status = "human_active"
    conversation.state = "human_active"
    conversation.assigned_user_id = current_user.id
    await db.commit()
    return conversation_summary_row(conversation)


@router.post("/conversations/{conversation_id}/reply", response_model=WhatsAppReplyResponse)
async def reply_to_conversation(
    conversation_id: UUID,
    payload: WhatsAppReplyRequest,
    current_user: Annotated[User, Depends(require_tenant_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhatsAppReplyResponse:
    result = await db.execute(
        select(WhatsAppConversation).where(
            WhatsAppConversation.tenant_id == current_user.tenant_id,
            WhatsAppConversation.id == conversation_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "CONVERSATION_NOT_FOUND", "message": "Conversation was not found."})
    conversation.status = "human_active"
    conversation.state = "human_active"
    conversation.assigned_user_id = current_user.id
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    message = await send_outbound_message(db, tenant=tenant, conversation=conversation, body=payload.body, sender_user_id=current_user.id)
    conversation.summary = conversation.summary or payload.body[:200]
    await db.commit()
    return WhatsAppReplyResponse(conversation_id=conversation.id, message_id=message.id, status=message.status)
