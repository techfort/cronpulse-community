import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    A service to send transactional emails using SMTP.
    Supports any SMTP server (Gmail, SendGrid, Mailgun, AWS SES, etc.)
    """

    def __init__(self, config: dict):
        """
        Initializes the EmailService with configuration.

        Args:
            config (dict): A dictionary containing configuration parameters.
                           Expected keys:
                           - 'SMTP_HOST': SMTP server hostname (e.g., smtp.gmail.com)
                           - 'SMTP_PORT': SMTP server port (e.g., 587 for TLS, 465 for SSL)
                           - 'SMTP_USER': SMTP username/email
                           - 'SMTP_PASSWORD': SMTP password or app password
                           - 'SENDER_EMAIL': The sender's email address
                           - 'SENDER_NAME': The sender's name
                           - 'SMTP_USE_TLS': Whether to use TLS (default: True)
        """
        required_keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "SENDER_NAME"]
        if not all(k in config for k in required_keys):
            raise ValueError(
                f"Config must contain: {', '.join(required_keys)}"
            )

        self.config = config
        self.smtp_host = config["SMTP_HOST"]
        self.smtp_port = int(config["SMTP_PORT"])
        self.smtp_user = config["SMTP_USER"]
        self.smtp_password = config["SMTP_PASSWORD"]
        self.sender_email = config["SENDER_EMAIL"]
        self.sender_name = config["SENDER_NAME"]
        self.use_tls = config.get("SMTP_USE_TLS", "true").lower() == "true"

    def send_alert(
        self, to_email: str, to_name: str, subject: str, html_content: str
    ) -> tuple[bool, str]:
        """
        Sends an email alert via SMTP.

        Args:
            to_email (str): The recipient's email address.
            to_name (str): The recipient's name.
            subject (str): The subject of the email.
            html_content (str): The HTML content of the email body.

        Returns:
            tuple[bool, str]: A tuple containing a boolean indicating success
                              and a message ("sent" on success, error on failure).
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = to_email

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Create secure connection and send
            context = ssl.create_default_context()
            
            if self.smtp_port == 465:
                # SSL connection
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)
            else:
                # TLS connection (port 587)
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True, "sent"
            
        except smtplib.SMTPAuthenticationError as e:
            error_message = f"SMTP authentication failed: {str(e)}"
            logger.error(error_message)
            return False, error_message
        except smtplib.SMTPException as e:
            error_message = f"SMTP error: {str(e)}"
            logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"Failed to send email: {str(e)}"
            logger.exception(error_message)
            return False, error_message
