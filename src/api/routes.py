from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import logging
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.models import (
    ReminderCreate, ReminderResponse,
    CampaignCreate, CampaignResponse,
    EmailLogResponse, StatsResponse, SendResult, HealthResponse
)
from src.config import Config
from src.email_sender import EmailSender
from main import load_contacts, load_template, personalize_email, run_automation


logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize shared instances
db = Database()
config = Config()
email_sender = EmailSender(config)


@router.get("/", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="Email Automation & Reminder System",
        version="1.0.0"
    )


@router.get("/reminders", response_model=List[ReminderResponse])
def list_reminders(status: Optional[str] = None):
    """List all reminders, optionally filtered by status."""
    reminders = db.get_reminders(status=status)
    return reminders


@router.post("/reminders", response_model=dict)
def create_reminder(reminder: ReminderCreate):
    """Create a new reminder."""
    reminder_id = db.add_reminder(
        reminder_id=reminder.reminder_id,
        contact_email=reminder.contact_email,
        subject=reminder.subject,
        template_name=reminder.template_name,
        schedule_time=reminder.schedule_time,
        message=reminder.message,
    )
    if reminder_id == -1:
        raise HTTPException(status_code=400, detail="Reminder ID already exists")
    return {"id": reminder_id, "message": "Reminder created successfully"}


@router.get("/reminders/{reminder_id}", response_model=ReminderResponse)
def get_reminder(reminder_id: str):
    """Get a specific reminder by ID."""
    reminder = db.get_reminder_by_id(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.get("/reminders/due", response_model=List[ReminderResponse])
def get_due_reminders():
    """Get reminders that are due for sending."""
    return db.get_due_reminders()


@router.post("/reminders/{reminder_id}/send", response_model=SendResult)
def send_reminder(reminder_id: str):
    """Send a specific reminder immediately."""
    reminder = db.get_reminder_by_id(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder["status"] == "sent":
        raise HTTPException(status_code=400, detail="Reminder already sent")

    # Load contacts and template
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contacts = load_contacts(os.path.join(base_dir, "data", "contacts.csv"))
    template = load_template(os.path.join(base_dir, "templates", "reminder.txt"))

    if contacts.empty or not template:
        raise HTTPException(status_code=500, detail="Failed to load contacts or template")

    # Find matching contact
    contact_email = reminder["contact_email"].lower()
    contact_lookup = {}
    for _, c in contacts.iterrows():
        contact_lookup[c.get("email", "").lower()] = c

    if contact_email not in contact_lookup:
        error_msg = f"No contact found for email: {contact_email}"
        db.update_reminder_status(reminder_id, "failed", error_message=error_msg)
        raise HTTPException(status_code=404, detail=error_msg)

    contact = contact_lookup[contact_email]
    subject, body = personalize_email(template, contact, reminder)

    # Send email
    result = email_sender.send(
        to_email=contact.get("email", ""),
        subject=subject,
        body=body,
    )

    timestamp = result.get("timestamp", "")
    if result["success"]:
        db.update_reminder_status(reminder_id, "sent", sent_at=timestamp)
        db.add_email_log(
            reminder_id=reminder_id,
            recipient=contact.get("email", ""),
            subject=subject,
            status="sent",
            message=result["message"],
            timestamp=timestamp,
        )
    else:
        db.update_reminder_status(reminder_id, "failed", error_message=result["message"])
        db.add_email_log(
            reminder_id=reminder_id,
            recipient=contact.get("email", ""),
            subject=subject,
            status="failed",
            message=result["message"],
            timestamp=timestamp,
        )

    return SendResult(
        success=result["success"],
        message=result["message"],
        timestamp=timestamp,
    )


@router.post("/send-due", response_model=dict)
def send_due_reminders(background_tasks: BackgroundTasks):
    """Send all due reminders."""
    due = db.get_due_reminders()

    if not due:
        return {"message": "No due reminders", "count": 0}

    # Run in background
    background_tasks.add_task(_process_due_reminders, due)

    return {"message": f"Processing {len(due)} due reminders", "count": len(due)}


def _process_due_reminders(due_reminders):
    """Background task to process due reminders."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contacts = load_contacts(os.path.join(base_dir, "data", "contacts.csv"))
    template = load_template(os.path.join(base_dir, "templates", "reminder.txt"))

    contact_lookup = {}
    for _, c in contacts.iterrows():
        contact_lookup[c.get("email", "").lower()] = c

    for reminder in due_reminders:
        reminder_id = reminder["reminder_id"]
        contact_email = reminder["contact_email"].lower()

        if contact_email not in contact_lookup:
            error_msg = f"No contact found for email: {contact_email}"
            db.update_reminder_status(reminder_id, "failed", error_message=error_msg)
            continue

        contact = contact_lookup[contact_email]
        subject, body = personalize_email(template, contact, reminder)

        result = email_sender.send(
            to_email=contact.get("email", ""),
            subject=subject,
            body=body,
        )

        timestamp = result.get("timestamp", "")
        if result["success"]:
            db.update_reminder_status(reminder_id, "sent", sent_at=timestamp)
            db.add_email_log(
                reminder_id=reminder_id,
                recipient=contact.get("email", ""),
                subject=subject,
                status="sent",
                message=result["message"],
                timestamp=timestamp,
            )
        else:
            db.update_reminder_status(reminder_id, "failed", error_message=result["message"])
            db.add_email_log(
                reminder_id=reminder_id,
                recipient=contact.get("email", ""),
                subject=subject,
                status="failed",
                message=result["message"],
                timestamp=timestamp,
            )


@router.get("/campaigns", response_model=List[CampaignResponse])
def list_campaigns():
    """List all campaigns."""
    return db.get_campaigns()


@router.post("/campaigns", response_model=dict)
def create_campaign(campaign: CampaignCreate):
    """Create a new campaign."""
    campaign_id = db.add_campaign(
        name=campaign.name,
        description=campaign.description,
        template_name=campaign.template_name,
    )
    return {"id": campaign_id, "message": "Campaign created successfully"}


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get system statistics."""
    return db.get_stats()


@router.get("/logs", response_model=List[EmailLogResponse])
def get_logs(limit: int = 100):
    """Get recent email logs."""
    return db.get_email_logs(limit=limit)


@router.post("/run")
def run_automation_endpoint(dry_run: bool = True):
    """Run the full automation workflow."""
    run_automation(dry_run=dry_run)
    stats = db.get_stats()
    return {"message": "Automation run completed", "stats": stats}
