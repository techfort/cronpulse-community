import brevo_python
from brevo_python.rest import ApiException


class EmailService:
    """
    A service to send transactional emails using the Brevo (formerly Sendinblue) API.
    """

    def __init__(self, config: dict):
        """
        Initializes the EmailService with configuration.

        Args:
            config (dict): A dictionary containing configuration parameters.
                           Expected keys:
                           - 'BREVO_API_KEY': Your Brevo API key.
                           - 'SENDER_EMAIL': The default sender's email address.
                           - 'SENDER_NAME': The default sender's name.
        """
        if not all(
            k in config for k in ["BREVO_API_KEY", "SENDER_EMAIL", "SENDER_NAME"]
        ):
            raise ValueError(
                "Config must contain BREVO_API_KEY, SENDER_EMAIL, and SENDER_NAME"
            )

        self.config = config
        self.sender_email = self.config["SENDER_EMAIL"]
        self.sender_name = self.config["SENDER_NAME"]

        # Configure API key authorization: api-key
        brevo_config = brevo_python.Configuration()
        brevo_config.api_key["api-key"] = self.config["BREVO_API_KEY"]

        # Create an instance of the API class
        api_client = brevo_python.ApiClient(brevo_config)
        self.api_instance = brevo_python.TransactionalEmailsApi(api_client)

    def send_alert(
        self, to_email: str, to_name: str, subject: str, html_content: str
    ) -> tuple[bool, str]:
        """
        Sends an email alert.

        Args:
            to_email (str): The recipient's email address.
            to_name (str): The recipient's name.
            subject (str): The subject of the email.
            html_content (str): The HTML content of the email body.

        Returns:
            tuple[bool, str]: A tuple containing a boolean indicating success
                              and a message (message_id on success, error on failure).
        """
        sender = brevo_python.SendSmtpEmailSender(
            name=self.sender_name, email=self.sender_email
        )
        to = [brevo_python.SendSmtpEmailTo(email=to_email, name=to_name)]

        send_smtp_email = brevo_python.SendSmtpEmail(
            sender=sender, to=to, html_content=html_content, subject=subject
        )

        try:
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            return True, api_response.message_id
        except ApiException as e:
            # It's recommended to log the full error `e` in a real application
            error_message = (
                "Exception when calling "
                f"TransactionalEmailsApi->send_transac_email: {e.reason}"
            )
            return False, error_message
