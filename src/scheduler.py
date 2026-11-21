import pandas as pd
import logging
from datetime import datetime
from src.config import Config


logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Reads reminders from CSV and determines which are due for sending."""

    def __init__(self, reminders_csv_path: str):
        self.reminders_csv_path = reminders_csv_path
        self.reminders = []

    def load_reminders(self):
        """Load reminders from CSV file."""
        try:
            self.reminders = pd.read_csv(self.reminders_csv_path)
            logger.info(f"Loaded {len(self.reminders)} reminders from {self.reminders_csv_path}")
            return self.reminders
        except FileNotFoundError:
            logger.error(f"Reminders file not found: {self.reminders_csv_path}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading reminders: {str(e)}")
            return pd.DataFrame()

    def get_due_reminders(self):
        """
        Get reminders that are due (schedule_time <= current time).

        Returns:
            pandas DataFrame of due reminders
        """
        if self.reminders.empty:
            return pd.DataFrame()

        now = datetime.now()
        due_reminders = []

        for _, row in self.reminders.iterrows():
            try:
                schedule_time = datetime.strptime(str(row["schedule_time"]), "%Y-%m-%d %H:%M:%S")
                if schedule_time <= now:
                    due_reminders.append(row)
            except ValueError as e:
                logger.warning(f"Invalid schedule_time for reminder {row.get('reminder_id', 'unknown')}: {str(e)}")

        if due_reminders:
            logger.info(f"Found {len(due_reminders)} due reminders")
            return pd.DataFrame(due_reminders)
        else:
            logger.info("No due reminders found")
            return pd.DataFrame()
