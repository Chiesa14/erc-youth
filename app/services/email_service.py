import smtplib
import urllib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import secrets
import string
from app.core.config import settings  # Assuming you have email config here

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

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
            frontend_url: str = "http://localhost:8080/change-password"
    ) -> bool:
        """Send invitation email to new family member with activation link"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = f"Welcome to {family_name} family - Set Up Your Account"

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

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()

            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
