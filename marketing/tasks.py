from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_waitlist_invite_email(email, token):
    """
    Sends an invitation email to the approved waitlist user.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.nishchinto.com.bd')
    claim_url = f"{frontend_url}/claim?token={token}"
    
    subject = "Your Nishchinto Beta Invite is Ready!"
    message = f"Congratulations! You've been approved. Click here to claim your shop: {claim_url}"
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
