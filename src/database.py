import sqlite3
import os
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class Database:
    """SQLite database connection manager for reminders and campaigns."""

    def __init__(self, db_path: str = "data/reminders.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        """Get a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                contact_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                template_name TEXT DEFAULT 'reminder.txt',
                schedule_time TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                sent_at TEXT,
                error_message TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                template_name TEXT DEFAULT 'reminder.txt',
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized at %s", self.db_path)

    def add_reminder(self, reminder_id: str, contact_email: str, subject: str,
                     template_name: str, schedule_time: str, message: str) -> int:
        """Add a new reminder to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute("""
                INSERT INTO reminders (reminder_id, contact_email, subject, template_name,
                                       schedule_time, message, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (reminder_id, contact_email, subject, template_name,
                  schedule_time, message, now))
            conn.commit()
            reminder_db_id = cursor.lastrowid
            logger.info("Added reminder %s to database", reminder_id)
            return reminder_db_id
        except sqlite3.IntegrityError as e:
            logger.error("Reminder %s already exists: %s", reminder_id, str(e))
            return -1
        finally:
            conn.close()

    def get_reminders(self, status: str = None):
        """Get all reminders, optionally filtered by status."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT * FROM reminders WHERE status = ? ORDER BY schedule_time", (status,))
        else:
            cursor.execute("SELECT * FROM reminders ORDER BY schedule_time")

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_reminder_by_id(self, reminder_id: str):
        """Get a single reminder by its reminder_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE reminder_id = ?", (reminder_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_reminder_status(self, reminder_id: str, status: str,
                               sent_at: str = None, error_message: str = None):
        """Update the status of a reminder."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if error_message:
            cursor.execute("""
                UPDATE reminders SET status = ?, sent_at = ?, error_message = ?
                WHERE reminder_id = ?
            """, (status, sent_at, error_message, reminder_id))
        else:
            cursor.execute("""
                UPDATE reminders SET status = ?, sent_at = ?
                WHERE reminder_id = ?
            """, (status, sent_at, reminder_id))

        conn.commit()
        conn.close()

    def get_due_reminders(self):
        """Get reminders that are due (schedule_time <= now and status = 'pending')."""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            SELECT * FROM reminders
            WHERE status = 'pending' AND schedule_time <= ?
            ORDER BY schedule_time
        """, (now,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_campaign(self, name: str, description: str, template_name: str) -> int:
        """Add a new campaign."""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO campaigns (name, description, template_name, status, created_at)
            VALUES (?, ?, ?, 'draft', ?)
        """, (name, description, template_name, now))
        conn.commit()
        campaign_id = cursor.lastrowid
        conn.close()
        return campaign_id

    def get_campaigns(self):
        """Get all campaigns."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_email_log(self, reminder_id: str, recipient: str, subject: str,
                      status: str, message: str, timestamp: str):
        """Add an email sending log entry."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_logs (reminder_id, recipient, subject, status, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (reminder_id, recipient, subject, status, message, timestamp))
        conn.commit()
        conn.close()

    def get_email_logs(self, limit: int = 100):
        """Get recent email logs."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM email_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self):
        """Get system statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM reminders")
        total_reminders = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM reminders WHERE status = 'sent'")
        sent_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM reminders WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM reminders WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]

        conn.close()
        return {
            "total_reminders": total_reminders,
            "sent": sent_count,
            "failed": failed_count,
            "pending": pending_count,
        }
