import uuid
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.database import get_db
from ...core.auth import get_current_account
from ...core.security import generate_webhook_secret, utcnow
from ...models.webhook import Webhook
from ...schemas.webhook import WebhookCreate, WebhookRead, WebhookCreateResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookCreateResponse, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    auth=Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    secret = generate_webhook_secret()
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()

    webhook = Webhook(
        account_id=account.id,
        url=body.url,
        secret_hash=secret_hash,
        description=body.description,
    )
    db.add(webhook)
    await db.flush()

    return WebhookCreateResponse(
        id=webhook.id,
        url=webhook.url,
        description=webhook.description,
        is_active=webhook.is_active,
        failure_count=webhook.failure_count,
        last_delivered_at=webhook.last_delivered_at,
        created_at=webhook.created_at,
        signing_secret=secret,
    )


@router.get("", response_model=list[WebhookRead])
async def list_webhooks(auth=Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    account, _ = auth
    result = await db.execute(select(Webhook).where(Webhook.account_id == account.id))
    return result.scalars().all()


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    auth=Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.account_id == account.id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)
