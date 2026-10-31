from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

from .choices import EQUIPMENT, GOALS, LEVELS
from .storage import DatabaseProfilePhotoStorage


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        storage=DatabaseProfilePhotoStorage(),
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )
    phone = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=80, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(13), MaxValueValidator(100)])
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(100), MaxValueValidator(250)])
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    goal = models.CharField(max_length=20, choices=GOALS, default="general")
    experience = models.CharField(max_length=20, choices=LEVELS, default="beginner")
    equipment = models.CharField(max_length=10, choices=EQUIPMENT, default="gym")
    days_per_week = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(2), MaxValueValidator(6)])
    is_premium = models.BooleanField(default=False, help_text="Reserved for future premium subscriptions.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user}"

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            m = self.height_cm / 100
            return round(float(self.weight_kg) / (m * m), 1)
        return None


class StoredProfilePhoto(models.Model):
    name = models.CharField(max_length=255, unique=True)
    content = models.BinaryField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmailVerification(models.Model):
    """One verification record per user; OTPs are stored as hashes, never plaintext."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_verification")
    code_hash = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    welcome_email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email verification for {self.user.email}"
