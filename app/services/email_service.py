import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import secrets
import string
from app.core.config import settings  # Assuming you have email config here


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

    def send_invitation_email(self, to_email: str, member_name: str, temp_password: str, family_name: str) -> bool:
        """Send invitation email to new family member"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = f"Welcome to {family_name} - Set Up Your Account"

            body = f"""
            Dear {member_name},

            You have been added to the {family_name} family system. To complete your account setup, please follow these steps:

            1. Use this temporary password to log in: {temp_password}
            2. After logging in, you will be prompted to create your own secure password
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
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()

            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False