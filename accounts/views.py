from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import PatientRegistrationForm
from .models import PatientProfile, StaffProfile

User = get_user_model()


def register(request):
    if request.user.is_authenticated:
        return redirect("customer_dashboard")
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            token = signing.dumps({"user_id": user.pk}, salt="medisearch-email-verification")
            verify_url = request.build_absolute_uri(reverse("verify_email", args=[token]))
            try:
                send_mail(
                    "Verify your MedMitra email",
                    f"Hello {user.first_name},\n\nVerify your email by opening:\n{verify_url}\n\nIf you did not create this account, ignore this email.",
                    settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False,
                )
                messages.success(request, "Account created. Check your email for the verification link.")
            except Exception:
                messages.warning(request, "Account created, but email delivery is not configured. You can continue and ask the administrator to configure SMTP.")
            login(request, user)
            return redirect("customer_dashboard")
    else:
        form = PatientRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def verify_email(request, token):
    try:
        data = signing.loads(token, salt="medisearch-email-verification", max_age=60 * 60 * 24)
        user = get_object_or_404(User, pk=data["user_id"])
        profile, _ = PatientProfile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])
        messages.success(request, "Email verified successfully.")
    except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError):
        messages.error(request, "This verification link is invalid or has expired.")
    return redirect("login")


@login_required
def dashboard(request):
    # Orders are the customer's main dashboard in the pharmacy-only application.
    return redirect("customer_dashboard")


@login_required
def role_dashboard(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect("marketplace_admin_dashboard")
    profile = StaffProfile.objects.filter(user=request.user).first()
    if not profile or profile.role not in {StaffProfile.Role.PHARMACIST, StaffProfile.Role.STORE_MANAGER}:
        messages.error(request, "This area is for authorised pharmacy staff.")
        return redirect("profile_overview")
    if not profile.is_approved:
        return render(request, "accounts/staff_pending.html", {"profile": profile})
    return redirect("pharmacy_dashboard")
