import pandas as pd
import logging
from datetime import datetime
import os


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates CSV reports and tracks email sending status."""

    def __init__(self, outputs_dir: str = "outputs"):
        self.outputs_dir = outputs_dir
        self.sent_emails = []
        self.failed_emails = []
        os.makedirs(self.outputs_dir, exist_ok=True)

    def log_sent(self, to_email: str, subject: str, timestamp: str, message: str = "Sent successfully"):
        """Record a successfully sent email."""
        self.sent_emails.append({
            "timestamp": timestamp,
            "recipient": to_email,
            "subject": subject,
            "status": "Sent",
            "message": message,
        })
        logger.info(f"Logged sent email to {to_email}")

    def log_failed(self, to_email: str, subject: str, timestamp: str, error_message: str):
        """Record a failed email attempt."""
        self.failed_emails.append({
            "timestamp": timestamp,
            "recipient": to_email,
            "subject": subject,
            "status": "Failed",
            "message": error_message,
        })
        logger.error(f"Logged failed email to {to_email}: {error_message}")

    def save_reports(self):
        """Save sent and failed email reports to CSV files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save sent emails report
        if self.sent_emails:
            sent_df = pd.DataFrame(self.sent_emails)
            sent_path = os.path.join(self.outputs_dir, f"sent_emails_{timestamp}.csv")
            sent_df.to_csv(sent_path, index=False)
            logger.info(f"Sent emails report saved to {sent_path}")
        else:
            sent_path = None
            logger.info("No sent emails to report")

        # Save failed emails report
        if self.failed_emails:
            failed_df = pd.DataFrame(self.failed_emails)
            failed_path = os.path.join(self.outputs_dir, f"failed_emails_{timestamp}.csv")
            failed_df.to_csv(failed_path, index=False)
            logger.info(f"Failed emails report saved to {failed_path}")
        else:
            failed_path = None
            logger.info("No failed emails to report")

        # Generate combined summary report
        summary = {
            "total_attempts": len(self.sent_emails) + len(self.failed_emails),
            "successful": len(self.sent_emails),
            "failed": len(self.failed_emails),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        summary_path = os.path.join(self.outputs_dir, f"report_{timestamp}.csv")
        pd.DataFrame([summary]).to_csv(summary_path, index=False)
        logger.info(f"Summary report saved to {summary_path}")

        return {
            "sent_path": sent_path,
            "failed_path": failed_path,
            "summary_path": summary_path,
            "summary": summary,
        }
