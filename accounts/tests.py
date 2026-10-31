from datetime import timedelta
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.mail import get_connection
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

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


class ProfilePhotoTests(TestCase):
    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.temp_media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.user = User.objects.create_user(
            username="photo-user",
            email="photo@example.com",
            password="ValidTestPass!932",
            first_name="Photo",
        )
        self.client.force_login(self.user)

    def make_photo(self, name="profile.png", image_format="PNG"):
        image = Image.new("RGB", (2, 2), color="green")
        content = BytesIO()
        image.save(content, format=image_format)
        return SimpleUploadedFile(name, content.getvalue(), content_type=f"image/{image_format.lower()}")

    def test_user_can_upload_and_view_profile_photo(self):
        response = self.client.post(reverse("accounts:profile"), {
            "photo": self.make_photo(),
            "phone": "",
            "city": "",
            "age": "",
            "height_cm": "",
            "weight_kg": "",
            "goal": "general",
            "experience": "beginner",
            "equipment": "gym",
            "days_per_week": "3",
        })

        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.photo.name.startswith("profile_photos/"))

        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, self.user.profile.photo.url)
        self.assertContains(response, 'class="profile-photo"')
        self.assertEqual(response.content.count(b'class="profile-photo"'), 1)
        self.assertContains(response, 'data-profile-photo-preview')
        self.assertContains(response, 'id="profile-photo-dialog"')
        self.assertContains(response, 'data-profile-photo-enlarged')
        self.assertContains(response, '<p class="profile-name">Photo</p>', html=True)
        self.assertContains(response, 'aria-label="Edit profile photo"')
        self.assertNotContains(response, "Maximum file size")
        self.assertNotContains(response, "JPG, PNG, or WebP")
        self.assertNotContains(response, "Currently:")
        self.assertNotContains(response, "Clear")

    def test_profile_photo_rejects_non_image_upload(self):
        response = self.client.post(reverse("accounts:profile"), {
            "photo": SimpleUploadedFile("profile.png", b"not an image", content_type="image/png"),
            "phone": "",
            "city": "",
            "age": "",
            "height_cm": "",
            "weight_kg": "",
            "goal": "general",
            "experience": "beginner",
            "equipment": "gym",
            "days_per_week": "3",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user.profile.photo)
