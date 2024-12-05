import requests
from django.conf import settings


BREVO_KEY = settings.BREVO_KEY


def ggsend_mail(receiver_email, subject, htmlContent):
    return requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json={
            "sender": {"name": "Dogesec", "email": "admin@dogesec.com"},
            "to": [{"email": receiver_email, "name": "John Doe"}],
            "subject": subject,
            "htmlContent": "<html><head></head><body><p>Hello,</p>This is my first transactional email sent from Brevo.</p></body></html>",
        },
        headers={
            "api-key": BREVO_KEY,
        },
    )
