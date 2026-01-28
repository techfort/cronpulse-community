#!/usr/bin/env python3
"""
Test SMTP email configuration by sending a test email.
Usage: python test_email.py recipient@example.com
"""
import sys
import os
from api.services.email_service import EmailService


def test_email(recipient: str):
    """Send a test email to verify SMTP configuration"""
    
    # Load configuration from environment
    config = {
        "SMTP_HOST": os.getenv("SMTP_HOST"),
        "SMTP_PORT": os.getenv("SMTP_PORT"),
        "SMTP_USER": os.getenv("SMTP_USER"),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD"),
        "SENDER_EMAIL": os.getenv("SENDER_EMAIL"),
        "SENDER_NAME": os.getenv("SENDER_NAME", "CronPulse"),
        "SMTP_USE_TLS": os.getenv("SMTP_USE_TLS", "true"),
    }
    
    # Check for missing configuration
    missing = [k for k, v in config.items() if not v and k != "SENDER_NAME" and k != "SMTP_USE_TLS"]
    if missing:
        print("❌ Missing SMTP configuration:")
        for key in missing:
            print(f"   - {key}")
        print("\nPlease set these environment variables in your .env file")
        print("See .env.example for reference")
        return False
    
    try:
        # Initialize email service
        print("📧 Initializing SMTP email service...")
        print(f"   Host: {config['SMTP_HOST']}:{config['SMTP_PORT']}")
        print(f"   User: {config['SMTP_USER']}")
        print(f"   Sender: {config['SENDER_NAME']} <{config['SENDER_EMAIL']}>")
        
        email_service = EmailService(config)
        
        # Send test email
        print(f"\n📤 Sending test email to {recipient}...")
        success, message = email_service.send_alert(
            to_email=recipient,
            to_name=recipient,
            subject="CronPulse SMTP Test",
            html_content="""
                <h2>✅ SMTP Configuration Test</h2>
                <p>Congratulations! Your CronPulse SMTP email configuration is working correctly.</p>
                <p>You can now receive email alerts when your monitors miss pings.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is a test email from CronPulse Community Edition
                </p>
            """
        )
        
        if success:
            print(f"✅ Test email sent successfully!")
            print(f"   Message: {message}")
            print(f"\nCheck {recipient} for the test email.")
            return True
        else:
            print(f"❌ Failed to send test email")
            print(f"   Error: {message}")
            return False
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_email.py recipient@example.com")
        sys.exit(1)
    
    recipient = sys.argv[1]
    success = test_email(recipient)
    sys.exit(0 if success else 1)
