import smtplib
import urllib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import secrets
import string
from app.core.config import settings  # Assuming you have email config here

try:
    import resend
except Exception:  # pragma: no cover
    resend = None

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.smtp_use_ssl = getattr(settings, "SMTP_USE_SSL", False)
        self.resend_api_key = getattr(settings, "RESEND_API_KEY", None)

    def _send_email_via_resend(self, to_email: str, subject: str, plain_body: str) -> bool:
        if not self.resend_api_key:
            return False
        if resend is None:
            logger.error("Resend is not installed but RESEND_API_KEY is set")
            return False

        try:
            resend.api_key = self.resend_api_key

            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": f"<pre>{plain_body}</pre>",
            }
            resend.Emails.send(params)
            return True
        except Exception as e:
            logger.error(f"Error sending email via Resend: {str(e)}")
            return False

    def _send_email_via_smtp(self, to_email: str, subject: str, plain_body: str) -> bool:
        server = None
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(plain_body, 'plain'))

            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, to_email, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {str(e)}")
            return False
        finally:
            try:
                if server is not None:
                    server.quit()
            except Exception:
                pass

    def generate_temporary_password(self, length: int = 12) -> str:
        """Generate a secure temporary password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))

    def send_invitation_email(
            self,
            to_email: str,
            member_name: str,
            temp_password: str,
            family_name: str,
            member_id: int,
            frontend_url: str = None
    ) -> bool:
        """Send invitation email to new family member with activation link"""
        try:
            # Use centralized configuration if no custom frontend_url is provided
            if frontend_url is None:
                frontend_url = settings.frontend_change_password_url
            
            subject = f"Welcome to {family_name} family - Set Up Your Account"

            encoded_temp_password = urllib.parse.quote(temp_password)
            activation_link = f"{frontend_url}?member_id={member_id}&temp_password={encoded_temp_password}"

            body = f"""
            Dear {member_name},

            You have been added to the {family_name} family system. To complete your account setup, please follow these steps:

            1. Click this link to set your password and activate your account:
               {activation_link}

            2. Your temporary password is: {temp_password}
            3. Your email address is: {to_email}

            Please keep this information secure and change your password immediately after your first login.

            If you have any questions, please contact your family administrator.

            Best regards,
            Family Management System
            """

            sent = self._send_email_via_resend(to_email=to_email, subject=subject, plain_body=body)
            if sent:
                return True
            return self._send_email_via_smtp(to_email=to_email, subject=subject, plain_body=body)
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False


    def send_user_invitation_email(
            self,
            to_email: str,
            user_name: str,
            temp_password: str,
            user_id: int,
            frontend_url: str = None
    ) -> bool:
        try:
            if frontend_url is None:
                frontend_url = settings.frontend_change_password_url

            subject = "Welcome - Set Up Your Account"

            encoded_temp_password = urllib.parse.quote(temp_password)
            activation_link = f"{frontend_url}?user_id={user_id}&temp_password={encoded_temp_password}"

            body = f"""
            Dear {user_name},

            An account has been created for you. To complete your account setup, please follow these steps:

            1. Click this link to set your password and activate your account:
               {activation_link}

            2. Your temporary password is: {temp_password}
            3. Your email address is: {to_email}

            Please keep this information secure and change your password immediately after your first login.

            Best regards,
            YouthTrack
            """

            sent = self._send_email_via_resend(to_email=to_email, subject=subject, plain_body=body)
            if sent:
                return True
            return self._send_email_via_smtp(to_email=to_email, subject=subject, plain_body=body)
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
