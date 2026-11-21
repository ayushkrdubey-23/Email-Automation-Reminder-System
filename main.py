import pandas as pd
import logging
import os
import sys
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.email_sender import EmailSender
from src.scheduler import ReminderScheduler
from src.report_generator import ReportGenerator


# Setup logging
def setup_logging(log_level: str = "INFO", logs_dir: str = "logs"):
    """Configure logging to file and console."""
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "email_automation.log")

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


def load_contacts(contacts_csv_path: str) -> pd.DataFrame:
    """Load contacts from CSV file."""
    try:
        contacts = pd.read_csv(contacts_csv_path)
        logger.info(f"Loaded {len(contacts)} contacts from {contacts_csv_path}")
        return contacts
    except FileNotFoundError:
        logger.error(f"Contacts file not found: {contacts_csv_path}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading contacts: {str(e)}")
        return pd.DataFrame()


def load_template(template_path: str) -> str:
    """Load email template from file."""
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
        logger.info(f"Loaded template from {template_path}")
        return template
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        return ""
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        return ""


def personalize_email(template: str, contact: pd.Series, reminder: pd.Series) -> tuple:
    """
    Personalize email template with contact and reminder data.

    Args:
        template: Email template string with placeholders
        contact: Contact row from contacts DataFrame
        reminder: Reminder row from reminders DataFrame

    Returns:
        tuple of (subject, body)
    """
    subject = reminder.get("subject", "Reminder")
    message = reminder.get("message", "")

    # Replace placeholders in body
    body = template.replace("{subject}", str(subject))
    body = body.replace("{name}", str(contact.get("name", "")))
    body = body.replace("{company}", str(contact.get("company", "")))
    body = body.replace("{department}", str(contact.get("department", "")))
    body = body.replace("{role}", str(contact.get("role", "")))
    body = body.replace("{message}", str(message))
    body = body.replace("{reminder_date}", str(reminder.get("schedule_time", "")))

    return subject, body


def run_automation(dry_run: bool = None):
    """
    Main automation workflow.

    Args:
        dry_run: Override dry_run setting from config. If None, uses config value.
    """
    # Load configuration
    config = Config()
    if dry_run is not None:
        config.dry_run = dry_run

    logger.info(f"Starting Email Automation & Reminder System")
    logger.info(f"Configuration: {config}")

    # File paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    contacts_path = os.path.join(base_dir, "data", "contacts.csv")
    reminders_path = os.path.join(base_dir, "data", "reminders.csv")
    template_path = os.path.join(base_dir, "templates", "reminder.txt")

    # Load data
    contacts = load_contacts(contacts_path)
    if contacts.empty:
        logger.error("No contacts loaded. Exiting.")
        return

    scheduler = ReminderScheduler(reminders_path)
    reminders = scheduler.load_reminders()
    if reminders.empty:
        logger.error("No reminders loaded. Exiting.")
        return

    template = load_template(template_path)
    if not template:
        logger.error("No template loaded. Exiting.")
        return

    # Initialize components
    email_sender = EmailSender(config)
    report_generator = ReportGenerator()

    # Get due reminders
    due_reminders = scheduler.get_due_reminders()

    if due_reminders.empty:
        logger.info("No reminders are due at this time.")
        report_generator.save_reports()
        return

    # Build contact lookup by email
    contact_lookup = {}
    for _, contact in contacts.iterrows():
        contact_lookup[contact.get("email", "").lower()] = contact

    # Process each due reminder
    for _, reminder in due_reminders.iterrows():
        reminder_id = reminder.get("reminder_id", "unknown")
        contact_email = reminder.get("contact_email", "").lower()

        # Find matching contact
        if contact_email not in contact_lookup:
            error_msg = f"No contact found for email: {contact_email}"
            logger.warning(f"[{reminder_id}] {error_msg}")
            report_generator.log_failed(
                to_email=contact_email,
                subject=reminder.get("subject", "Unknown"),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                error_message=error_msg,
            )
            continue

        contact = contact_lookup[contact_email]

        # Personalize email
        subject, body = personalize_email(template, contact, reminder)

        # Send email
        result = email_sender.send(
            to_email=contact.get("email", ""),
            subject=subject,
            body=body,
        )

        # Log result
        timestamp = result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if result["success"]:
            report_generator.log_sent(
                to_email=contact.get("email", ""),
                subject=subject,
                timestamp=timestamp,
                message=result["message"],
            )
        else:
            report_generator.log_failed(
                to_email=contact.get("email", ""),
                subject=subject,
                timestamp=timestamp,
                error_message=result["message"],
            )

    # Save reports
    report_paths = report_generator.save_reports()

    # Print summary
    summary = report_paths["summary"]
    print("\n" + "=" * 50)
    print("EMAIL AUTOMATION SUMMARY")
    print("=" * 50)
    print(f"Total attempts: {summary['total_attempts']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Generated at: {summary['generated_at']}")
    print("=" * 50)
    print(f"Reports saved in: outputs/")
    print("=" * 50 + "\n")


def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI API server."""
    import uvicorn
    from src.api.app import app

    logger.info(f"Starting API server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Email Automation & Reminder System")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (simulate sending without actual emails)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send actual emails (requires SMTP credentials in .env)",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start the FastAPI API server",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)",
    )
    args = parser.parse_args()

    # API server mode
    if args.api:
        setup_logging()
        run_api_server(host=args.host, port=args.port)
        sys.exit(0)

    # Determine dry_run mode
    if args.send:
        dry_run = False
    elif args.dry_run:
        dry_run = True
    else:
        # Default to dry-run mode for safety
        dry_run = None  # Use config value (defaults to True)

    setup_logging()
    run_automation(dry_run=dry_run)
