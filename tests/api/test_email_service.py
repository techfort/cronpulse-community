"""
Tests for the SMTP EmailService
"""
import pytest
from unittest.mock import patch, MagicMock
from api.services.email_service import EmailService


class TestEmailService:
    """Test EmailService with SMTP"""

    def test_init_with_valid_config(self):
        """Test EmailService initializes with valid configuration"""
        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "test@example.com",
            "SMTP_PASSWORD": "test_password",
            "SENDER_EMAIL": "noreply@example.com",
            "SENDER_NAME": "Test Service",
        }
        service = EmailService(config)
        assert service.smtp_host == "smtp.gmail.com"
        assert service.smtp_port == 587
        assert service.sender_email == "noreply@example.com"
        assert service.use_tls is True

    def test_init_with_missing_config(self):
        """Test EmailService raises error with missing configuration"""
        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
        }
        with pytest.raises(ValueError) as exc_info:
            EmailService(config)
        assert "Config must contain" in str(exc_info.value)

    @patch("api.services.email_service.smtplib.SMTP")
    def test_send_alert_success_tls(self, mock_smtp):
        """Test sending email successfully via TLS"""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "test@example.com",
            "SMTP_PASSWORD": "test_password",
            "SENDER_EMAIL": "noreply@example.com",
            "SENDER_NAME": "Test Service",
            "SMTP_USE_TLS": "true",
        }
        service = EmailService(config)

        # Send email
        success, message = service.send_alert(
            to_email="recipient@example.com",
            to_name="Recipient",
            subject="Test Alert",
            html_content="<p>Test email</p>",
        )

        # Verify
        assert success is True
        assert message == "sent"
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.send_message.assert_called_once()

    @patch("api.services.email_service.smtplib.SMTP_SSL")
    def test_send_alert_success_ssl(self, mock_smtp_ssl):
        """Test sending email successfully via SSL (port 465)"""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_server

        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "test@example.com",
            "SMTP_PASSWORD": "test_password",
            "SENDER_EMAIL": "noreply@example.com",
            "SENDER_NAME": "Test Service",
        }
        service = EmailService(config)

        # Send email
        success, message = service.send_alert(
            to_email="recipient@example.com",
            to_name="Recipient",
            subject="Test Alert",
            html_content="<p>Test email</p>",
        )

        # Verify
        assert success is True
        assert message == "sent"
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.send_message.assert_called_once()

    @patch("api.services.email_service.smtplib.SMTP")
    def test_send_alert_authentication_error(self, mock_smtp):
        """Test handling SMTP authentication errors"""
        from smtplib import SMTPAuthenticationError

        # Setup mock to raise authentication error
        mock_server = MagicMock()
        mock_server.login.side_effect = SMTPAuthenticationError(535, "Authentication failed")
        mock_smtp.return_value.__enter__.return_value = mock_server

        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "test@example.com",
            "SMTP_PASSWORD": "wrong_password",
            "SENDER_EMAIL": "noreply@example.com",
            "SENDER_NAME": "Test Service",
        }
        service = EmailService(config)

        # Send email
        success, message = service.send_alert(
            to_email="recipient@example.com",
            to_name="Recipient",
            subject="Test Alert",
            html_content="<p>Test email</p>",
        )

        # Verify
        assert success is False
        assert "authentication failed" in message.lower()

    @patch("api.services.email_service.smtplib.SMTP")
    def test_send_alert_generic_error(self, mock_smtp):
        """Test handling generic SMTP errors"""
        # Setup mock to raise generic exception
        mock_server = MagicMock()
        mock_server.send_message.side_effect = Exception("Connection timeout")
        mock_smtp.return_value.__enter__.return_value = mock_server

        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "test@example.com",
            "SMTP_PASSWORD": "test_password",
            "SENDER_EMAIL": "noreply@example.com",
            "SENDER_NAME": "Test Service",
        }
        service = EmailService(config)

        # Send email
        success, message = service.send_alert(
            to_email="recipient@example.com",
            to_name="Recipient",
            subject="Test Alert",
            html_content="<p>Test email</p>",
        )

        # Verify
        assert success is False
        assert "Failed to send email" in message
