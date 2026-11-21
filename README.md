# Email Automation & Reminder System

A Python-based system that schedules and sends automated emails (one-off or recurring), tracks delivery status, and fires personal/team reminders. Built with CSV contact lists, email templates, Gmail/SMTP simulation, and local scheduling. Ideal for students building a portfolio project.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Overview

The **Email Automation & Reminder System** automates repetitive email communication for HR, sales, trainers, operations, and business teams. It reads contacts and reminders from CSV files, personalizes email templates, schedules sends based on time, delivers via SMTP (Gmail), and generates delivery reports.

## Problem Statement

Sending reminder emails manually is repetitive, error-prone, and doesn't scale. Teams often forget to send:
- Interview and meeting reminders
- Payment due alerts
- Webinar and event notifications
- Follow-up emails to leads and clients
- Task and deadline notifications

This system solves that by automating the entire workflow from contact list to delivery report.

## Industry Relevance

| Role | Use Case |
|------|----------|
| HR Teams | Interview reminders, offer follow-ups, onboarding sequences |
| Sales Teams | Lead follow-ups, demo reminders, proposal check-ins |
| Trainers | Webinar reminders, class schedules, assignment deadlines |
| Operations | Payment due alerts, task notifications, vendor reminders |
| Business/Productivity | Recurring newsletters, anniversary wishes, deadline alerts |

## Features

- Read contacts and reminders from CSV files
- Personalize email templates with `{name}`, `{company}`, `{department}`, `{role}`, `{message}`, `{reminder_date}`, `{subject}`
- Schedule reminders by comparing `schedule_time` against current time
- Send emails via Gmail SMTP using `smtplib`
- Dry-run mode for safe testing without sending real emails
- Track delivery status (sent/failed) with timestamps
- Generate CSV reports (sent, failed, summary)
- Logging to file and console via `logging` module
- Secure credential management via `.env` and `python-dotenv`
- Modular, beginner-friendly code structure

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.9+ |
| Data handling | pandas |
| Email sending | smtplib, email.message |
| Scheduling | schedule, datetime |
| Configuration | python-dotenv |
| Logging | logging (built-in) |
| Data format | CSV |
| Environment | Virtual environment (venv) |

## Folder Structure

```
Email-Automation-Reminder-System/
├── data/                 # Input CSV files (contacts.csv, reminders.csv)
├── templates/            # Email body templates with placeholders
├── src/                  # Python source code (modular)
│   ├── config.py         # Configuration from environment variables
│   ├── email_sender.py   # SMTP email sending with dry-run support
│   ├── scheduler.py      # Reminder scheduling logic
│   └── report_generator.py # CSV report generation
├── outputs/              # Generated reports (sent_emails, failed_emails, report)
├── logs/                 # Execution logs (email_automation.log)
├── images/               # Screenshots for README/GitHub
├── docs/                 # Additional documentation
├── main.py               # Entry point
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables (no secrets)
├── .gitignore            # Git ignore rules
└── README.md             # Project documentation
```

## Setup Instructions

### 1. Clone the repository
```powershell
git clone https://github.com/YOUR_USERNAME/Email-Automation-Reminder-System.git
cd Email-Automation-Reminder-System
```

### 2. Create and activate virtual environment
**Windows:**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and update with your values:
```powershell
Copy-Item .env.example .env
```

Edit `.env`:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
DRY_RUN=True
LOG_LEVEL=INFO
```

> **Important:** Use a Gmail App Password, not your regular Gmail password. Never commit `.env` to GitHub.

## How to Run

### Dry-run mode (recommended for testing)
Simulates sending without connecting to SMTP. No real emails are sent.
```powershell
python main.py --dry-run
```

### Actual email mode
Sends real emails via Gmail SMTP. Requires configured `.env` credentials.
```powershell
python main.py --send
```

### Expected output (dry-run)
```
Starting Email Automation & Reminder System
Configuration: Config(..., dry_run=True)
Loaded 6 contacts from data/contacts.csv
Loaded 6 reminders from data/reminders.csv
Found 6 due reminders
[DRY-RUN] Would send email to john.doe@example.com with subject: Project Deadline Reminder
...
EMAIL AUTOMATION SUMMARY
Total attempts: 6
Successful: 6
Failed: 0
Reports saved in: outputs/
```

### Generated files
- `logs/email_automation.log` — detailed execution log
- `outputs/sent_emails_<timestamp>.csv` — successful sends
- `outputs/failed_emails_<timestamp>.csv` — failures (if any)
- `outputs/report_<timestamp>.csv` — summary report

## Sample Output

**sent_emails.csv:**
```
timestamp,recipient,subject,status,message
2026-11-21 17:15:31,john.doe@example.com,Project Deadline Reminder,Sent,Dry-run mode - email simulated
2026-11-21 17:15:31,jane.smith@example.com,Interview Scheduled,Sent,Dry-run mode - email simulated
```

**report_*.csv:**
```
total_attempts,successful,failed,generated_at
6,6,0,2026-11-21 17:15:31
```

## Screenshots

Add screenshots to the `images/` folder:
1. Terminal output of dry-run mode
2. Generated CSV reports
3. Log file contents

## Learning Outcomes

By building this project, you will learn:
- Reading and writing CSV files with pandas
- Personalizing email templates with string replacement
- Sending emails via SMTP with `smtplib` and `email.message`
- Scheduling tasks based on datetime comparisons
- Error handling and exception management
- Logging to file and console
- Generating CSV reports
- Secure credential management with environment variables
- Building modular, maintainable Python code
- GitHub best practices (.gitignore, .env.example, README)

## Security

- Never upload `.env` with real passwords — it is listed in `.gitignore`
- Use `.env.example` as a template for others
- Use Gmail App Passwords, not regular passwords
- Do not commit real contact email addresses or secrets

## License

MIT License

---

**Built as a Python course project — proof of work for Python Developer, Automation, Operations, HR, Admin, and Business Productivity roles.**
