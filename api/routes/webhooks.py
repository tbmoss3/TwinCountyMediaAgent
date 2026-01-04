"""
Webhook endpoints for Mailchimp callbacks.
"""
from fastapi import APIRouter, Request, HTTPException
import logging
from datetime import datetime

from database.connection import get_database
from database.repositories.newsletter_repository import NewsletterRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


@router.post("/mailchimp")
async def mailchimp_webhook(request: Request):
    """
    Handle Mailchimp webhook callbacks.

    Mailchimp sends webhooks for:
    - Campaign sent
    - Campaign opens
    - Campaign clicks
    - Unsubscribes
    """
    try:
        # Get webhook data
        data = await request.json()

        webhook_type = data.get("type")
        webhook_data = data.get("data", {})

        logger.info(f"Received Mailchimp webhook: {webhook_type}")

        if webhook_type == "campaign":
            # Campaign event (sent, opened, clicked)
            campaign_id = webhook_data.get("id")

            if campaign_id:
                db = get_database()
                newsletter_repo = NewsletterRepository(db)

                # Find newsletter by campaign ID
                query = """
                SELECT id FROM sent_newsletters
                WHERE mailchimp_campaign_id = $1
                """
                row = await db.fetchrow(query, campaign_id)

                if row:
                    # Update metrics if available
                    if "emails_sent" in webhook_data:
                        await newsletter_repo.update_metrics(
                            row['id'],
                            recipients_count=webhook_data.get("emails_sent", 0),
                            opens_count=webhook_data.get("unique_opens", 0),
                            clicks_count=webhook_data.get("clicks", 0)
                        )

        return {"status": "received", "type": webhook_type}

    except Exception as e:
        logger.error(f"Error processing Mailchimp webhook: {e}")
        # Return 200 to prevent Mailchimp from retrying
        return {"status": "error", "message": str(e)}


@router.get("/mailchimp/verify")
async def verify_mailchimp_webhook():
    """
    Verify endpoint for Mailchimp webhook setup.

    Mailchimp sends a GET request to verify the webhook URL is valid.
    """
    return {
        "status": "verified",
        "service": "TwinCountyMediaAgent",
        "timestamp": datetime.now().isoformat()
    }
