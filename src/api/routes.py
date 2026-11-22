from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import sys
import os
import tempfile
import shutil

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.models import (
    ReminderCreate, ReminderResponse,
    CampaignCreate, CampaignResponse,
    EmailLogResponse, StatsResponse, SendResult, HealthResponse,
    ContactResponse, ContactUploadResult,
    ReminderUpdate, CampaignUpdate, ReportFile
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


# ========== REMINDERS ==========

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


@router.put("/reminders/{reminder_id}", response_model=dict)
def update_reminder(reminder_id: str, updates: ReminderUpdate):
    """Update an existing reminder."""
    reminder = db.get_reminder_by_id(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    success = db.update_reminder(reminder_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reminder")

    return {"message": "Reminder updated successfully"}


@router.delete("/reminders/{reminder_id}", response_model=dict)
def delete_reminder(reminder_id: str):
    """Delete a reminder."""
    reminder = db.get_reminder_by_id(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    success = db.delete_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete reminder")

    return {"message": "Reminder deleted successfully"}


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


# ========== CAMPAIGNS ==========

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


@router.put("/campaigns/{campaign_id}", response_model=dict)
def update_campaign(campaign_id: int, updates: CampaignUpdate):
    """Update an existing campaign."""
    campaigns = db.get_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    success = db.update_campaign(campaign_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update campaign")

    return {"message": "Campaign updated successfully"}


@router.delete("/campaigns/{campaign_id}", response_model=dict)
def delete_campaign(campaign_id: int):
    """Delete a campaign."""
    campaigns = db.get_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    success = db.delete_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete campaign")

    return {"message": "Campaign deleted successfully"}


# ========== CONTACTS ==========

@router.get("/contacts", response_model=List[ContactResponse])
def list_contacts():
    """List all contacts from CSV file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contacts_path = os.path.join(base_dir, "data", "contacts.csv")
    contacts = db.get_contacts_from_csv(contacts_path)
    return contacts


@router.post("/contacts/upload", response_model=ContactUploadResult)
def upload_contacts(file: UploadFile = File(...)):
    """Upload and import contacts from CSV file."""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        result = db.upload_contacts_from_csv(tmp_path)

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass

        return ContactUploadResult(
            success=result["success"],
            message=result["message"],
            imported=result["imported"],
            total=result["total"],
            invalid=result["invalid"],
        )
    except Exception as e:
        logger.error("Error uploading contacts: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ========== STATS ==========

@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get system statistics."""
    return db.get_stats()


# ========== LOGS ==========

@router.get("/logs", response_model=List[EmailLogResponse])
def get_logs(limit: int = 100):
    """Get recent email logs."""
    return db.get_email_logs(limit=limit)


# ========== REPORTS ==========

@router.get("/reports", response_model=List[ReportFile])
def list_reports():
    """List all generated report files."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_path = os.path.join(base_dir, "outputs")
    reports = db.get_report_files(outputs_path)
    return reports


@router.get("/reports/download/{filename}")
def download_report(filename: str):
    """Download a report file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_path = os.path.join(base_dir, "outputs")
    file_path = os.path.join(outputs_path, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="text/csv",
    )


# ========== AUTOMATION ==========

@router.post("/run")
def run_automation_endpoint(dry_run: bool = True):
    """Run the full automation workflow."""
    run_automation(dry_run=dry_run)
    stats = db.get_stats()
    return {"message": "Automation workflow completed", "stats": stats}
