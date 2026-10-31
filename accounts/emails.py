import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _brand_context(user):
    main, _, accent = settings.SITE_NAME.rpartition(" ")
    if not main:
        main, accent = settings.SITE_NAME, ""
    return {
        "user": user,
        "name": user.first_name or user.username,
        "site_url": settings.SITE_URL.rstrip("/"),
        "site_name": settings.SITE_NAME,
        "brand_main": main,
        "brand_accent": accent,
    }


def send_verification_email(user, code):
    """Send a short-lived email OTP. Returns True only when backend accepts the message."""
    if not user.email:
        return False
    ctx = _brand_context(user)
    ctx.update({"code": code, "expiry_minutes": 10})
    try:
        message = EmailMultiAlternatives(
            f"Your {settings.SITE_NAME} verification code",
            render_to_string("emails/verification.txt", ctx),
            settings.DEFAULT_FROM_EMAIL, [user.email],
        )
        message.attach_alternative(render_to_string("emails/verification.html", ctx), "text/html")
        return message.send(fail_silently=False) == 1
    except Exception:
        logger.exception("Verification email could not be sent for user id %s", user.pk)
        return False


def send_welcome_email(user):
    """Send branded welcome email. Never blocks a successfully verified account."""
    if not user.email:
        return False
    ctx = _brand_context(user)
    try:
        message = EmailMultiAlternatives(
            f"Welcome to {settings.SITE_NAME} — Your Fitness Journey Starts Here!",
            render_to_string("emails/welcome.txt", ctx),
            settings.DEFAULT_FROM_EMAIL, [user.email],
        )
        message.attach_alternative(render_to_string("emails/welcome.html", ctx), "text/html")
        return message.send(fail_silently=False) == 1
    except Exception:
        logger.exception("Welcome email failed for user id %s", user.pk)
        return False
