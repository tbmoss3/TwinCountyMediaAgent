"""
Mailchimp integration service for newsletter delivery.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError

from config.settings import get_settings

logger = logging.getLogger(__name__)


class MailchimpService:
    """Service for Mailchimp newsletter operations."""

    def __init__(self):
        """Initialize Mailchimp service."""
        self.settings = get_settings()
        self.client = MailchimpMarketing.Client()
        self.client.set_config({
            "api_key": self.settings.mailchimp_api_key,
            "server": self.settings.mailchimp_server_prefix
        })

    async def create_campaign(
        self,
        subject_line: str,
        preview_text: str,
        html_content: str,
        plain_text_content: str = None
    ) -> Dict[str, Any]:
        """
        Create a new Mailchimp campaign.

        Args:
            subject_line: Email subject line
            preview_text: Preview text shown in inbox
            html_content: HTML content of the email
            plain_text_content: Plain text version (optional)

        Returns:
            Dict with campaign_id and web_id
        """
        try:
            # Create the campaign
            campaign_data = {
                "type": "regular",
                "recipients": {
                    "list_id": self.settings.mailchimp_list_id
                },
                "settings": {
                    "subject_line": subject_line,
                    "preview_text": preview_text,
                    "from_name": self.settings.mailchimp_from_name,
                    "reply_to": self.settings.mailchimp_reply_to,
                    "title": f"Twin County Weekly - {datetime.now().strftime('%Y-%m-%d')}"
                }
            }

            campaign = self.client.campaigns.create(campaign_data)
            campaign_id = campaign["id"]

            logger.info(f"Created Mailchimp campaign: {campaign_id}")

            # Set the content
            content_data = {"html": html_content}
            if plain_text_content:
                content_data["plain_text"] = plain_text_content

            self.client.campaigns.set_content(campaign_id, content_data)

            logger.info(f"Set content for campaign {campaign_id}")

            return {
                "campaign_id": campaign_id,
                "web_id": campaign.get("web_id"),
                "status": "created"
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error creating campaign: {e.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating Mailchimp campaign: {e}")
            raise

    async def send_test_email(
        self,
        campaign_id: str,
        test_emails: List[str]
    ) -> Dict[str, Any]:
        """
        Send test email to preview recipients.

        Args:
            campaign_id: Mailchimp campaign ID
            test_emails: List of email addresses for preview

        Returns:
            Dict with status and recipients
        """
        try:
            self.client.campaigns.send_test_email(
                campaign_id,
                {"test_emails": test_emails, "send_type": "html"}
            )

            logger.info(f"Sent test email for campaign {campaign_id} to {test_emails}")

            return {
                "status": "test_sent",
                "recipients": test_emails
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error sending test: {e.text}")
            raise
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            raise

    async def schedule_campaign(
        self,
        campaign_id: str,
        send_time: datetime
    ) -> Dict[str, Any]:
        """
        Schedule campaign for future delivery.

        Args:
            campaign_id: Mailchimp campaign ID
            send_time: When to send the campaign

        Returns:
            Dict with status and scheduled time
        """
        try:
            self.client.campaigns.schedule(
                campaign_id,
                {"schedule_time": send_time.isoformat()}
            )

            logger.info(f"Scheduled campaign {campaign_id} for {send_time}")

            return {
                "status": "scheduled",
                "scheduled_for": send_time.isoformat()
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error scheduling: {e.text}")
            raise
        except Exception as e:
            logger.error(f"Error scheduling campaign: {e}")
            raise

    async def send_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """
        Send campaign immediately.

        Args:
            campaign_id: Mailchimp campaign ID

        Returns:
            Dict with status and sent time
        """
        try:
            self.client.campaigns.send(campaign_id)

            logger.info(f"Sent campaign {campaign_id}")

            return {
                "status": "sent",
                "sent_at": datetime.now().isoformat()
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error sending campaign: {e.text}")
            raise
        except Exception as e:
            logger.error(f"Error sending campaign: {e}")
            raise

    async def get_campaign_report(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get campaign performance report.

        Args:
            campaign_id: Mailchimp campaign ID

        Returns:
            Dict with campaign metrics
        """
        try:
            report = self.client.reports.get_campaign_report(campaign_id)

            return {
                "campaign_id": campaign_id,
                "emails_sent": report.get("emails_sent", 0),
                "opens": report.get("opens", {}).get("opens_total", 0),
                "unique_opens": report.get("opens", {}).get("unique_opens", 0),
                "open_rate": report.get("opens", {}).get("open_rate", 0),
                "clicks": report.get("clicks", {}).get("clicks_total", 0),
                "unique_clicks": report.get("clicks", {}).get("unique_subscriber_clicks", 0),
                "click_rate": report.get("clicks", {}).get("click_rate", 0),
                "unsubscribes": report.get("unsubscribed", 0)
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error getting report: {e.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting campaign report: {e}")
            raise

    async def health_check(self) -> bool:
        """Check Mailchimp API connectivity."""
        try:
            self.client.ping.get()
            return True
        except Exception as e:
            logger.error(f"Mailchimp health check failed: {e}")
            return False

    async def get_list_stats(self) -> Dict[str, Any]:
        """Get audience/list statistics."""
        try:
            list_info = self.client.lists.get_list(self.settings.mailchimp_list_id)

            return {
                "list_id": self.settings.mailchimp_list_id,
                "name": list_info.get("name"),
                "member_count": list_info.get("stats", {}).get("member_count", 0),
                "unsubscribe_count": list_info.get("stats", {}).get("unsubscribe_count", 0),
                "campaign_count": list_info.get("stats", {}).get("campaign_count", 0),
                "avg_open_rate": list_info.get("stats", {}).get("avg_open_rate", 0),
                "avg_click_rate": list_info.get("stats", {}).get("avg_click_rate", 0)
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error getting list stats: {e.text}")
            raise
