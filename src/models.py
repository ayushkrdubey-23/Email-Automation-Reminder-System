from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


class ReminderCreate(BaseModel):
    reminder_id: str
    contact_email: EmailStr
    subject: str
    template_name: Optional[str] = "reminder.txt"
    schedule_time: str
    message: str


class ReminderResponse(BaseModel):
    id: int
    reminder_id: str
    contact_email: str
    subject: str
    template_name: str
    schedule_time: str
    message: str
    status: str
    created_at: str
    sent_at: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_name: Optional[str] = "reminder.txt"


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    template_name: str
    status: str
    created_at: str
    sent_count: int
    failed_count: int

    class Config:
        from_attributes = True


class EmailLogResponse(BaseModel):
    id: int
    reminder_id: Optional[str] = None
    recipient: str
    subject: str
    status: str
    message: Optional[str] = None
    timestamp: str

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_reminders: int
    sent: int
    failed: int
    pending: int


class SendResult(BaseModel):
    success: bool
    message: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
