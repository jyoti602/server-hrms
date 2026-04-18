import os
import smtplib
import logging
from pathlib import Path
from email.message import EmailMessage
from typing import Iterable, Sequence

from dotenv import load_dotenv
from pydantic import EmailStr, TypeAdapter

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

_email_adapter = TypeAdapter(EmailStr)
logger = logging.getLogger(__name__)
DEFAULT_APP_LOGIN_URL = "https://hrms-ui.netlify.app"


class EmailNotificationError(Exception):
    """Base exception for email notification failures."""


class InvalidEmailError(EmailNotificationError):
    """Raised when a recipient email address is invalid."""


class SMTPConfigurationError(EmailNotificationError):
    """Raised when SMTP settings are missing or malformed."""


class SMTPConnectionFailure(EmailNotificationError):
    """Raised when the SMTP server cannot be reached or rejects the message."""


def _normalize_email(address: str) -> str:
    try:
        return str(_email_adapter.validate_python(address))
    except Exception as exc:
        raise InvalidEmailError(f"Invalid email address: {address}") from exc


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_smtp_config() -> dict | None:
    username = os.getenv("SMTP_USERNAME", os.getenv("EMAIL_USER", "")).strip()
    password = os.getenv("SMTP_PASSWORD", os.getenv("EMAIL_PASS", "")).strip().replace(" ", "")
    host = os.getenv("SMTP_HOST", os.getenv("EMAIL_HOST", "")).strip()
    port_raw = os.getenv("SMTP_PORT", os.getenv("EMAIL_PORT", "587")).strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", username).strip()
    use_tls = _parse_bool(os.getenv("SMTP_USE_TLS"), default=True)
    use_ssl = _parse_bool(os.getenv("SMTP_USE_SSL"), default=False)
    timeout_raw = os.getenv("SMTP_TIMEOUT", "20").strip()

    if not host and username.endswith("@gmail.com"):
        host = "smtp.gmail.com"

    if not host or not username or not password or not from_email:
        return None

    try:
        port = int(port_raw)
        timeout = int(timeout_raw)
    except ValueError as exc:
        raise SMTPConfigurationError("SMTP_PORT and SMTP_TIMEOUT must be valid integers") from exc

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from_email": _normalize_email(from_email),
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "timeout": timeout,
    }


def send_email(
    recipient: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    config = _get_smtp_config()
    if not config:
        logger.warning("SMTP is not configured; skipping email to %s", recipient)
        return

    message = EmailMessage()
    message["From"] = config["from_email"]
    message["To"] = _normalize_email(recipient)
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if config["use_ssl"]:
            smtp_client: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
                config["host"],
                config["port"],
                timeout=config["timeout"],
            )
        else:
            smtp_client = smtplib.SMTP(
                config["host"],
                config["port"],
                timeout=config["timeout"],
            )

        with smtp_client as smtp:
            if config["use_tls"] and not config["use_ssl"]:
                smtp.starttls()
            smtp.login(config["username"], config["password"])
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise SMTPConnectionFailure(f"Failed to send email to {recipient}") from exc


def send_company_registration_notification(
    company_email: str,
    company_slug: str,
    company_name: str,
    admin_username: str,
    admin_password: str,
    login_link: str | None = None,
) -> None:
    login_text = login_link or os.getenv("APP_LOGIN_URL", "").strip() or DEFAULT_APP_LOGIN_URL
    body = "\n".join(
        [
            "Company Registration Successful",
            "",
            f"Company Slug: {company_slug}",
            f"Company Name: {company_name}",
            f"Admin Username: {admin_username}",
            f"Admin Password: {admin_password}",
            f"Login Instructions: {login_text}",
        ]
    )
    send_email(company_email, "Company Registration Successful", body)


def send_employee_account_notification(
    employee_email: str,
    company_slug: str,
    username: str,
    password: str,
    login_link: str | None = None,
) -> None:
    login_text = login_link or os.getenv("APP_LOGIN_URL", "").strip() or DEFAULT_APP_LOGIN_URL
    body = "\n".join(
        [
            "Your Account Has Been Created",
            "",
            f"Company Slug: {company_slug}",
            f"Username: {username}",
            f"Password: {password}",
            f"Login Link: {login_text}",
        ]
    )
    send_email(employee_email, "Your Account Has Been Created", body)


def send_leave_application_notification(
    admin_emails: Sequence[str] | Iterable[str],
    company_slug: str,
    employee_name: str,
    leave_type: str,
    from_date,
    to_date,
    reason: str,
) -> None:
    recipients = [_normalize_email(email) for email in admin_emails if email]
    if not recipients:
        raise InvalidEmailError("No admin email addresses were provided")

    config = _get_smtp_config()
    if not config:
        logger.warning("SMTP is not configured; skipping leave notification for %s", employee_name)
        return

    message = EmailMessage()
    message["From"] = config["from_email"]
    message["To"] = ", ".join(recipients)
    message["Subject"] = "New Leave Application"
    message.set_content(
        "\n".join(
        [
            "New Leave Application",
            "",
            f"Company Slug: {company_slug}",
            f"Employee Name: {employee_name}",
            f"Leave Type: {leave_type}",
            f"Leave Dates: {from_date} to {to_date}",
            f"Reason: {reason}",
        ]
        )
    )

    try:
        if config["use_ssl"]:
            smtp_client = smtplib.SMTP_SSL(
                config["host"],
                config["port"],
                timeout=config["timeout"],
            )
        else:
            smtp_client = smtplib.SMTP(
                config["host"],
                config["port"],
                timeout=config["timeout"],
            )

        with smtp_client as smtp:
            if config["use_tls"] and not config["use_ssl"]:
                smtp.starttls()
            smtp.login(config["username"], config["password"])
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise SMTPConnectionFailure("Failed to send leave application notification") from exc


def send_leave_status_notification(
    employee_email: str,
    company_slug: str,
    employee_name: str,
    leave_type: str,
    from_date,
    to_date,
    status: str,
    admin_comment: str | None = None,
    login_link: str | None = None,
) -> None:
    login_text = login_link or os.getenv("APP_LOGIN_URL", "").strip() or DEFAULT_APP_LOGIN_URL
    normalized_status = status.strip().lower()
    subject = "Leave Request Approved" if normalized_status == "approved" else "Leave Request Rejected"
    body_lines = [
        f"Leave Request {status.title()}",
        "",
        f"Company Slug: {company_slug}",
        f"Employee Name: {employee_name}",
        f"Leave Type: {leave_type}",
        f"Leave Dates: {from_date} to {to_date}",
        f"Status: {status.title()}",
        f"Login Link: {login_text}",
    ]
    if admin_comment:
        body_lines.extend(["", f"Admin Comment: {admin_comment}"])

    send_email(
        employee_email,
        subject,
        "\n".join(body_lines),
    )
