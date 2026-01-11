import smtplib
import urllib
import logging
import html
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

        self.brand_name = getattr(settings, "EMAIL_BRAND_NAME", "YouthTrack")
        self.brand_color = getattr(settings, "EMAIL_BRAND_COLOR", "#2563EB")
        self.brand_logo_url = getattr(settings, "EMAIL_LOGO_URL", None)

    def _build_email_html(
            self,
            *,
            title: str,
            greeting_name: str,
            intro: str,
            action_text: str,
            action_url: str,
            details: list[tuple[str, str]] | None = None,
            footer_note: str | None = None,
    ) -> str:
        safe_title = html.escape(title)
        safe_greeting_name = html.escape(greeting_name)
        safe_intro = html.escape(intro)
        safe_action_text = html.escape(action_text)
        safe_action_url = html.escape(action_url)

        details_html = ""
        if details:
            rows = []
            for label, value in details:
                rows.append(
                    """
                    <tr>
                      <td style=\"padding: 6px 0; color: #475569; font-size: 14px;\"><strong>{label}</strong></td>
                      <td style=\"padding: 6px 0; color: #0f172a; font-size: 14px; text-align: right;\">{value}</td>
                    </tr>
                    """.format(label=html.escape(label), value=html.escape(value))
                )
            details_html = (
                """
                <div style=\"margin-top: 18px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px;\">
                  <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"border-collapse: collapse;\">
                    {rows}
                  </table>
                </div>
                """.format(rows="".join(rows))
            )

        footer_html = ""
        if footer_note:
            footer_html = """
              <p style=\"margin: 18px 0 0; color: #64748b; font-size: 12px; line-height: 18px;\">
                {footer_note}
              </p>
            """.format(footer_note=html.escape(footer_note))

        logo_html = ""
        if self.brand_logo_url:
            logo_html = """
              <img src=\"{logo}\" alt=\"{brand}\" height=\"32\" style=\"display:block; border:0; outline:none; text-decoration:none;\" />
            """.format(logo=html.escape(self.brand_logo_url), brand=html.escape(self.brand_name))
        else:
            logo_html = """
              <div style=\"font-size: 18px; font-weight: 700; color: #0f172a;\">{brand}</div>
            """.format(brand=html.escape(self.brand_name))

        return """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <meta name=\"x-apple-disable-message-reformatting\" />
    <title>{title}</title>
  </head>
  <body style=\"margin:0; padding:0; background:#f1f5f9;\">
    <div style=\"display:none; max-height:0; overflow:hidden; opacity:0; color:transparent;\">{title}</div>
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f1f5f9; padding: 24px 12px;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"600\" cellspacing=\"0\" cellpadding=\"0\" style=\"width:100%; max-width:600px;\">
            <tr>
              <td style=\"padding: 8px 6px 16px;\">{logo_html}</td>
            </tr>
            <tr>
              <td style=\"background:#ffffff; border-radius:16px; padding: 22px 20px; border: 1px solid #e2e8f0;\">
                <h1 style=\"margin: 0 0 10px; font-size: 20px; line-height: 28px; color: #0f172a;\">{title}</h1>
                <p style=\"margin: 0 0 12px; color: #0f172a; font-size: 14px; line-height: 22px;\">Dear {name},</p>
                <p style=\"margin: 0; color: #334155; font-size: 14px; line-height: 22px;\">{intro}</p>

                <div style=\"margin-top: 18px;\">
                  <a href=\"{action_url}\" style=\"display:inline-block; background:{brand_color}; color:#ffffff; text-decoration:none; padding: 12px 16px; border-radius: 10px; font-weight: 600; font-size: 14px;\">{action_text}</a>
                </div>

                <p style=\"margin: 14px 0 0; color: #64748b; font-size: 12px; line-height: 18px;\">
                  If the button doesn’t work, copy and paste this link into your browser:<br />
                  <a href=\"{action_url}\" style=\"color:{brand_color}; word-break: break-all;\">{action_url}</a>
                </p>

                {details_html}

                {footer_html}
              </td>
            </tr>
            <tr>
              <td style=\"padding: 14px 6px 0; color:#94a3b8; font-size: 12px; line-height: 18px;\" align=\"center\">
                Sent by {brand}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>""".format(
            title=safe_title,
            name=safe_greeting_name,
            intro=safe_intro,
            action_text=safe_action_text,
            action_url=safe_action_url,
            brand_color=html.escape(self.brand_color),
            brand=html.escape(self.brand_name),
            details_html=details_html,
            footer_html=footer_html,
            logo_html=logo_html,
        )

    def _send_email_via_resend(self, to_email: str, subject: str, plain_body: str, html_body: Optional[str] = None) -> bool:
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
                "text": plain_body,
                "html": html_body or f"<pre>{html.escape(plain_body)}</pre>",
            }
            resend.Emails.send(params)
            return True
        except Exception as e:
            logger.error(f"Error sending email via Resend: {str(e)}")
            return False

    def _send_email_via_smtp(self, to_email: str, subject: str, plain_body: str, html_body: Optional[str] = None) -> bool:
        server = None
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))

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

            body = "\n".join(
                [
                    f"Dear {member_name},",
                    "",
                    f"You have been added to the {family_name} family system. Use the link below to set your password and activate your account.",
                    "",
                    f"Activation link: {activation_link}",
                    "",
                    f"Temporary password: {temp_password}",
                    f"Email: {to_email}",
                    "",
                    "Please keep this information secure and change your password immediately after your first login.",
                    "",
                    f"Best regards,",
                    f"{self.brand_name}",
                ]
            )

            html_body = self._build_email_html(
                title=subject,
                greeting_name=member_name,
                intro=f"You have been added to the {family_name} family system. To complete your account setup, please activate your account below.",
                action_text="Activate account",
                action_url=activation_link,
                details=[
                    ("Temporary password", temp_password),
                    ("Email", to_email),
                ],
                footer_note="For your security, change your password immediately after your first login.",
            )

            sent = self._send_email_via_resend(to_email=to_email, subject=subject, plain_body=body, html_body=html_body)
            if sent:
                return True
            return self._send_email_via_smtp(to_email=to_email, subject=subject, plain_body=body, html_body=html_body)
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

            body = "\n".join(
                [
                    f"Dear {user_name},",
                    "",
                    "An account has been created for you. Use the link below to set your password and activate your account.",
                    "",
                    f"Activation link: {activation_link}",
                    "",
                    f"Temporary password: {temp_password}",
                    f"Email: {to_email}",
                    "",
                    "Please keep this information secure and change your password immediately after your first login.",
                    "",
                    f"Best regards,",
                    f"{self.brand_name}",
                ]
            )

            html_body = self._build_email_html(
                title=subject,
                greeting_name=user_name,
                intro="An account has been created for you. To complete your account setup, please activate your account below.",
                action_text="Set password & activate",
                action_url=activation_link,
                details=[
                    ("Temporary password", temp_password),
                    ("Email", to_email),
                ],
                footer_note="For your security, change your password immediately after your first login.",
            )

            sent = self._send_email_via_resend(to_email=to_email, subject=subject, plain_body=body, html_body=html_body)
            if sent:
                return True
            return self._send_email_via_smtp(to_email=to_email, subject=subject, plain_body=body, html_body=html_body)
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
