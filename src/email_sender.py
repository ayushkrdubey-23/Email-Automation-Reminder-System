import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime
from src.config import Config


logger = logging.getLogger(__name__)


class EmailSender:
    """Handles sending emails via SMTP with dry-run support."""

    def __init__(self, config: Config):
        self.config = config

    def send(self, to_email: str, subject: str, body: str) -> dict:
        """
        Send an email to a recipient.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content

        Returns:
            dict with keys: success (bool), message (str), timestamp (str)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Dry-run mode: simulate sending without actually sending
        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would send email to {to_email} with subject: {subject}")
            return {
                "success": True,
                "message": "Dry-run mode - email simulated",
                "timestamp": timestamp,
            }

        # Check if credentials are configured
        if not self.config.is_configured():
            error_msg = "Email credentials not configured. Set SENDER_EMAIL and SENDER_PASSWORD in .env"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": timestamp,
            }

        try:
            msg = EmailMessage()
            msg["From"] = self.config.sender_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "timestamp": timestamp,
            }

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": timestamp,
            }
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": timestamp,
            }
        except Exception as e:
            error_msg = f"Unexpected error sending to {to_email}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": timestamp,
            }
