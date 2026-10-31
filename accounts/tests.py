from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.mail import get_connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerification


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SITE_URL="https://example.test")
class EmailVerificationFlowTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_TIMEOUT=7,
    )
    def test_smtp_connection_uses_configured_timeout(self):
        self.assertEqual(get_connection().timeout, 7)

    def test_registration_creates_inactive_user_and_sends_code(self):
        response = self.client.post(reverse("accounts:register"), {
            "first_name": "Test", "username": "testuser", "email": "test@example.com",
            "password1": "ValidTestPass!932", "password2": "ValidTestPass!932",
        })
        self.assertRedirects(response, reverse("accounts:verify_email"))
        user = User.objects.get(username="testuser")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verification code", mail.outbox[0].subject.lower())
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())

    def test_wrong_code_does_not_activate_account(self):
        user = User.objects.create_user(username="testuser", email="test@example.com", password="ValidTestPass!932", is_active=False)
        EmailVerification.objects.create(user=user, code_hash="wronghash", expires_at=timezone.now() + timedelta(minutes=10), last_sent_at=timezone.now())
        session = self.client.session
        session["pending_verification_user_id"] = user.pk
        session.save()
        self.client.post(reverse("accounts:verify_email"), {"code": "123456"})
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_correct_code_activates_and_sends_welcome_once(self):
        from .views import _hash_code
        user = User.objects.create_user(username="testuser", email="test@example.com", password="ValidTestPass!932", is_active=False, first_name="Test")
        EmailVerification.objects.create(user=user, code_hash=_hash_code("123456"), expires_at=timezone.now() + timedelta(minutes=10), last_sent_at=timezone.now())
        session = self.client.session
        session["pending_verification_user_id"] = user.pk
        session.save()
        response = self.client.post(reverse("accounts:verify_email"), {"code": "123456"})
        self.assertRedirects(response, reverse("accounts:verification_success"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to", mail.outbox[0].subject)
        record = EmailVerification.objects.get(user=user)
        self.assertIsNotNone(record.welcome_email_sent_at)
        self.client.get(reverse("accounts:verification_success"))
        self.assertEqual(len(mail.outbox), 1)
