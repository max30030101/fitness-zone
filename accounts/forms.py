from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Profile


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=60, label="First name")
    email = forms.EmailField(label="Email address")

    class Meta:
        model = User
        fields = ("first_name", "username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try signing in or verifying your account instead.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        user.first_name = self.cleaned_data["first_name"].strip()
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or email", widget=forms.TextInput(attrs={"autofocus": True}))

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError("This account is not active yet. Verify your email first: use the Resend Verification Code link below.", code="inactive")
        super().confirm_login_allowed(user)


class ProfileForm(forms.ModelForm):
    MAX_PHOTO_SIZE = 5 * 1024 * 1024

    class Meta:
        model = Profile
        fields = ["photo", "phone", "city", "age", "height_cm", "weight_kg", "goal", "experience", "equipment", "days_per_week"]
        labels = {
            "photo": "Profile photo",
            "height_cm": "Height (cm)",
            "weight_kg": "Weight (kg)",
            "experience": "Experience level",
            "days_per_week": "Workout days per week",
        }
        widgets = {
            "photo": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "hidden": True}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > self.MAX_PHOTO_SIZE:
            raise forms.ValidationError("Choose an image smaller than 5 MB.")
        return photo
