import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings loaded from environment variables."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.dry_run = os.getenv("DRY_RUN", "True").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    def is_configured(self):
        """Check if email credentials are configured."""
        return bool(self.sender_email and self.sender_password)

    def __str__(self):
        return (
            f"Config(smtp_server={self.smtp_server}, "
            f"smtp_port={self.smtp_port}, "
            f"sender_email={self.sender_email}, "
            f"dry_run={self.dry_run})"
        )
