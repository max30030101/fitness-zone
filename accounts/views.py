import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .emails import send_verification_email, send_welcome_email
from .forms import ProfileForm, RegisterForm
from .models import EmailVerification

OTP_TTL_MINUTES = 10
OTP_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


def _hash_code(code):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{code}".encode("utf-8")).hexdigest()


def _issue_code(user, *, force=False):
    """Create and email an OTP; enforce a server-side resend cooldown."""
    record, _ = EmailVerification.objects.get_or_create(user=user)
    now = timezone.now()
    if record.verified_at:
        return "verified"
    if record.last_sent_at and not force:
        remaining = OTP_RESEND_SECONDS - int((now - record.last_sent_at).total_seconds())
        if remaining > 0:
            return f"wait:{remaining}"
    code = f"{secrets.randbelow(1_000_000):06d}"
    record.code_hash = _hash_code(code)
    record.expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
    record.attempts = 0
    record.last_sent_at = now
    record.save()
    if not send_verification_email(user, code):
        return "email_failed"
    return "sent"


def register(request):
    if request.user.is_authenticated:
        return redirect("workouts:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        # The Profile post_save signal continues to create the user's profile.
        request.session["pending_verification_user_id"] = user.pk
        result = _issue_code(user, force=True)
        if result == "email_failed":
            messages.error(request, "Your account was created, but the email could not be sent. Use Resend Code on the verification page after checking email settings.")
        else:
            messages.success(request, "Account created. Enter the 6-digit code sent to your email to activate your account.")
        return redirect("accounts:verify_email")
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_email(request):
    user_id = request.session.get("pending_verification_user_id")
    user = User.objects.filter(pk=user_id).first() if user_id else None
    if not user:
        messages.info(request, "Enter the email address you registered with to request a verification code.")
        return redirect("accounts:resend_verification")
    record, _ = EmailVerification.objects.get_or_create(user=user)
    if record.verified_at and user.is_active:
        messages.info(request, "This email address is already verified. Please sign in.")
        request.session.pop("pending_verification_user_id", None)
        return redirect("accounts:login")
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        now = timezone.now()
        if record.attempts >= OTP_MAX_ATTEMPTS:
            messages.error(request, "Too many incorrect attempts. Request a new code after the resend cooldown.")
        elif not code.isdigit() or len(code) != 6:
            messages.error(request, "Enter the 6-digit code from your email.")
        elif not record.expires_at or now >= record.expires_at:
            messages.error(request, "This code has expired. Please request a new code.")
        elif not secrets.compare_digest(record.code_hash, _hash_code(code)):
            record.attempts += 1
            record.save(update_fields=["attempts"])
            messages.error(request, "That code is incorrect. Please try again.")
        else:
            with transaction.atomic():
                record.verified_at = now
                record.code_hash = ""
                record.expires_at = None
                record.save(update_fields=["verified_at", "code_hash", "expires_at"])
                user.is_active = True
                user.save(update_fields=["is_active"])
            login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
            request.session.pop("pending_verification_user_id", None)
            sent = send_welcome_email(user)
            if sent:
                record.welcome_email_sent_at = timezone.now()
                record.save(update_fields=["welcome_email_sent_at"])
                messages.success(request, f"Email verified successfully. Welcome to {settings.SITE_NAME}! Your welcome email has been sent.")
            else:
                messages.warning(request, "Email verified successfully. The welcome email could not be sent right now; you can retry it from your account.")
            return redirect("accounts:verification_success")
    remaining = max(0, int((record.expires_at - timezone.now()).total_seconds())) if record.expires_at else 0
    return render(request, "accounts/verify_email.html", {
        "email": user.email,
        "masked_email": _mask_email(user.email),
        "seconds_remaining": remaining,
        "can_resend": not record.last_sent_at or (timezone.now() - record.last_sent_at).total_seconds() >= OTP_RESEND_SECONDS,
    })


def _mask_email(email):
    try:
        name, domain = email.split("@", 1)
        visible = name[:1] if name else "*"
        return f"{visible}{'*' * max(2, len(name) - 1)}@{domain}"
    except ValueError:
        return "your email address"


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        # Generic response avoids disclosing whether an email has an account.
        if user:
            result = _issue_code(user)
            if result.startswith("wait:"):
                messages.info(request, f"Please wait {result.split(':', 1)[1]} seconds before requesting another code.")
            elif result == "email_failed":
                messages.error(request, "The code could not be emailed. Please try again later or contact the site administrator.")
            else:
                request.session["pending_verification_user_id"] = user.pk
                messages.success(request, "If this account needs verification, a code has been sent.")
        else:
            messages.info(request, "If this account needs verification, a code has been sent.")
        return redirect("accounts:verify_email") if request.session.get("pending_verification_user_id") else redirect("accounts:resend_verification")
    return render(request, "accounts/resend_verification.html")


@login_required
def retry_welcome_email(request):
    record = EmailVerification.objects.filter(user=request.user, verified_at__isnull=False).first()
    if not record:
        messages.error(request, "Your email verification record was not found. Please contact support.")
    elif record.welcome_email_sent_at:
        messages.info(request, "Your welcome email has already been sent.")
    elif send_welcome_email(request.user):
        record.welcome_email_sent_at = timezone.now()
        record.save(update_fields=["welcome_email_sent_at"])
        messages.success(request, "Your welcome email has been sent.")
    else:
        messages.error(request, "The welcome email could not be sent. Please try again later.")
    return redirect("accounts:profile")


@login_required
def verification_success(request):
    return render(request, "accounts/verification_success.html", {
        "welcome_email_sent": EmailVerification.objects.filter(user=request.user, welcome_email_sent_at__isnull=False).exists()
    })


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved. New plans will use these settings.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
