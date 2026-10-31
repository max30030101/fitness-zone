from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import LoginForm

app_name = "accounts"
_brand = {"brand": settings.SITE_NAME}

urlpatterns = [
    path("profile-photo/<path:filename>", views.profile_photo, name="profile_photo"),
    path("register/", views.register, name="register"),
    path("verify-email/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("verification-success/", views.verification_success, name="verification_success"),
    path("retry-welcome-email/", views.retry_welcome_email, name="retry_welcome_email"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html", authentication_form=LoginForm, redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html", email_template_name="emails/password_reset_email.txt", subject_template_name="emails/password_reset_subject.txt", success_url=reverse_lazy("accounts:password_reset_done"), extra_email_context=_brand), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html", success_url=reverse_lazy("accounts:password_reset_complete")), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
]
