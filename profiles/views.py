from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import PatientProfile, StaffProfile
from marketplace.models import MarketplaceAuditLog, MarketplaceOrder, MedicineProduct, Pharmacy, PharmacyListing, Prescription
from .forms import (
    AccountDetailsForm,
    CustomerAddressForm,
    DeletionRequestForm,
    PharmacyBusinessForm,
    ProfilePreferencesForm,
    ProfilePersonalForm,
)
from .models import AccountDeletionRequest, CustomerAddress, ProfilePreferences, SavedMedicine, SavedPharmacy

User = get_user_model()


def _preferences_for(user):
    prefs, created = ProfilePreferences.objects.get_or_create(user=user)
    # Keep the established profile/contact values in sync rather than replacing existing profile models.
    if created:
        patient = PatientProfile.objects.filter(user=user).first()
        staff = StaffProfile.objects.filter(user=user).first()
        if patient:
            prefs.contact_phone = patient.phone
            prefs.date_of_birth = patient.date_of_birth
        elif staff:
            prefs.contact_phone = staff.phone
        prefs.save(update_fields=["contact_phone", "date_of_birth", "updated_at"])
    return prefs


def _role_context(user):
    pharmacies = Pharmacy.objects.filter(owner=user).order_by("name")
    staff_profile = StaffProfile.objects.filter(user=user).first()
    patient_profile = PatientProfile.objects.filter(user=user).first()
    if user.is_superuser:
        role = "Administrator"
    elif pharmacies.exists():
        role = "Retailer / Pharmacy Owner"
    elif staff_profile:
        role = "Pharmacy Staff"
    elif user.is_staff:
        role = "Site Staff"
    else:
        role = "Customer"
    return {
        "role_label": role,
        "owned_pharmacies": pharmacies,
        "staff_profile": staff_profile,
        "patient_profile": patient_profile,
        "prefs": _preferences_for(user),
    }


def _audit(actor, action, obj, details=""):
    """Log only the action type and record reference, never passwords, uploads or changed field values."""
    MarketplaceAuditLog.objects.create(
        actor=actor,
        action=action[:60],
        object_type=obj._meta.label_lower if hasattr(obj, "_meta") else str(obj)[:100],
        object_id=str(getattr(obj, "pk", obj))[:64],
        details=details[:500],
    )


def _customer_orders(user):
    return MarketplaceOrder.objects.filter(customer=user).select_related("pharmacy", "prescription").prefetch_related("items")


def _retailer_stats(pharmacies):
    today = timezone.localdate()
    soon = today + timedelta(days=30)
    listings = PharmacyListing.objects.filter(pharmacy__in=pharmacies)
    orders = MarketplaceOrder.objects.filter(pharmacy__in=pharmacies)
    sellable = F("available_quantity") - F("reserved_quantity")
    in_stock = listings.filter(active=True, available_quantity__gt=F("reserved_quantity")).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)
    )
    completed_sales = orders.filter(status=MarketplaceOrder.Status.COMPLETED).aggregate(total=Sum("total"))["total"] or 0
    return [
        {"label": "Active listings", "value": listings.filter(active=True).count(), "icon": "bi-capsule"},
        {"label": "In-stock listings", "value": in_stock.count(), "icon": "bi-check2-circle"},
        {"label": "Out of stock", "value": listings.filter(active=True).filter(available_quantity__lte=F("reserved_quantity")).count(), "icon": "bi-box"},
        {"label": "Low stock (5 or fewer)", "value": listings.annotate(_sellable=sellable).filter(active=True, _sellable__gt=0, _sellable__lte=5).count(), "icon": "bi-exclamation-triangle"},
        {"label": "Expiring within 30 days", "value": listings.filter(active=True, expiry_date__range=(today, soon)).count(), "icon": "bi-calendar2-week"},
        {"label": "Expired listings", "value": listings.filter(active=True, expiry_date__lt=today).count(), "icon": "bi-calendar-x"},
        {"label": "Pending orders", "value": orders.filter(status=MarketplaceOrder.Status.PENDING).count(), "icon": "bi-hourglass-split"},
        {"label": "Completed sales", "value": f"₹{completed_sales:,.2f}", "icon": "bi-currency-rupee"},
    ]


@login_required
def profile_overview(request):
    context = _role_context(request.user)
    role = context["role_label"]
    context["orders"] = _customer_orders(request.user)[:5]
    context["prescriptions"] = Prescription.objects.filter(owner=request.user)[:5]
    context["addresses"] = CustomerAddress.objects.filter(user=request.user)[:3]
    context["saved_pharmacy_count"] = SavedPharmacy.objects.filter(user=request.user).count()
    context["saved_medicine_count"] = SavedMedicine.objects.filter(user=request.user).count()
    context["deletion_request"] = AccountDeletionRequest.objects.filter(user=request.user).first()

    if role == "Customer":
        all_orders = MarketplaceOrder.objects.filter(customer=request.user)
        context["stats"] = [
            {"label": "Total orders", "value": all_orders.count(), "icon": "bi-bag-check"},
            {"label": "In progress", "value": all_orders.filter(status__in=[MarketplaceOrder.Status.PENDING, MarketplaceOrder.Status.ACCEPTED, MarketplaceOrder.Status.PROCESSING, MarketplaceOrder.Status.READY, MarketplaceOrder.Status.OUT_FOR_DELIVERY]).count(), "icon": "bi-hourglass-split"},
            {"label": "Completed", "value": all_orders.filter(status=MarketplaceOrder.Status.COMPLETED).count(), "icon": "bi-check-circle"},
            {"label": "Cancelled", "value": all_orders.filter(status=MarketplaceOrder.Status.CANCELLED).count(), "icon": "bi-x-circle"},
        ]
    elif role == "Retailer / Pharmacy Owner":
        context["stats"] = _retailer_stats(context["owned_pharmacies"])
        context["retailer_orders"] = MarketplaceOrder.objects.filter(pharmacy__in=context["owned_pharmacies"]).select_related("customer", "pharmacy").order_by("-created_at")[:6]
        context["owned_pharmacies"] = context["owned_pharmacies"][:5]
    elif role == "Administrator":
        context["audit_events"] = MarketplaceAuditLog.objects.select_related("actor").order_by("-created_at")[:8]
        context["stats"] = [
            {"label": "Customers", "value": User.objects.filter(is_staff=False, is_superuser=False, staff_profile__isnull=True, owned_pharmacies__isnull=True).distinct().count(), "icon": "bi-people"},
            {"label": "Pharmacies", "value": Pharmacy.objects.count(), "icon": "bi-shop"},
            {"label": "Pending verification", "value": Pharmacy.objects.filter(verification_status=Pharmacy.VerificationStatus.PENDING).count(), "icon": "bi-shield-exclamation"},
            {"label": "Deletion requests", "value": AccountDeletionRequest.objects.filter(status=AccountDeletionRequest.Status.PENDING).count(), "icon": "bi-person-x"},
        ]
    else:
        context["stats"] = [
            {"label": "Staff role", "value": context["staff_profile"].get_role_display() if context["staff_profile"] else "Staff", "icon": "bi-person-badge"},
            {"label": "Account status", "value": "Approved" if context["staff_profile"] and context["staff_profile"].is_approved else "Pending / not configured", "icon": "bi-shield-check"},
        ]
    return render(request, "profiles/overview.html", context)


@login_required
def profile_edit(request):
    context = _role_context(request.user)
    prefs = context["prefs"]
    old_email = request.user.email
    patient_profile = context["patient_profile"]
    was_verified = bool(patient_profile and patient_profile.email_verified)
    requested_pharmacy_id = request.POST.get("pharmacy") or request.GET.get("pharmacy")
    owned_pharmacies = context["owned_pharmacies"]
    pharmacy = owned_pharmacies.filter(pk=requested_pharmacy_id).first() if requested_pharmacy_id else owned_pharmacies.first()

    if request.method == "POST":
        account_form = AccountDetailsForm(request.POST, instance=request.user)
        personal_form = ProfilePersonalForm(request.POST, request.FILES, instance=prefs)
        business_form = PharmacyBusinessForm(request.POST, instance=pharmacy) if pharmacy else None
        valid_results = [account_form.is_valid(), personal_form.is_valid()]
        if business_form is not None:
            valid_results.append(business_form.is_valid())
        if all(valid_results):
            with transaction.atomic():
                account = account_form.save()
                personal = personal_form.save()
                if patient_profile:
                    patient_profile.phone = personal.contact_phone
                    patient_profile.date_of_birth = personal.date_of_birth
                    if old_email.strip().lower() != account.email.strip().lower() and was_verified:
                        patient_profile.email_verified = False
                    patient_profile.save(update_fields=["phone", "date_of_birth", "email_verified"])
                staff_profile = context["staff_profile"]
                if staff_profile:
                    staff_profile.phone = personal.contact_phone
                    staff_profile.save(update_fields=["phone"])
                if business_form is not None:
                    business_form.save()
                _audit(request.user, "profile_updated", request.user, "Account profile and preferences updated")
                if business_form is not None:
                    _audit(request.user, "pharmacy_profile_updated", pharmacy, "Owner updated permitted business details")
            if old_email.strip().lower() != account.email.strip().lower() and was_verified:
                token = signing.dumps({"user_id": account.pk}, salt="medikhoj-email-verification")
                verify_url = request.build_absolute_uri(reverse("verify_email", args=[token]))
                try:
                    send_mail(
                        "Verify your updated MedMitra email",
                        f"Hello {account.first_name or account.username},\n\nVerify your updated email address by opening:\n{verify_url}\n\nIf you did not make this change, contact the platform administrator.",
                        settings.DEFAULT_FROM_EMAIL,
                        [account.email],
                        fail_silently=False,
                    )
                    messages.success(request, "Profile saved. A new email verification link has been sent to your updated address.")
                except Exception:
                    messages.warning(request, "Profile saved, but email delivery is not configured. The previous email verification is no longer valid; configure SMTP before relying on email verification.")
            else:
                messages.success(request, "Your profile has been updated.")
            return redirect("profile_overview")
        messages.error(request, "Please correct the errors below.")
    else:
        account_form = AccountDetailsForm(instance=request.user)
        personal_form = ProfilePersonalForm(instance=prefs)
        business_form = PharmacyBusinessForm(instance=pharmacy) if pharmacy else None

    context.update({"account_form": account_form, "personal_form": personal_form, "business_form": business_form, "pharmacy_editing": pharmacy})
    return render(request, "profiles/edit.html", context)


@login_required
def address_list(request):
    context = _role_context(request.user)
    context["addresses"] = CustomerAddress.objects.filter(user=request.user)
    return render(request, "profiles/addresses.html", context)


@login_required
def address_edit(request, pk=None):
    context = _role_context(request.user)
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user) if pk else None
    if request.method == "POST":
        form = CustomerAddressForm(request.POST, instance=address)
        if form.is_valid():
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.user = request.user
                should_default = bool(form.cleaned_data.get("is_default")) or not CustomerAddress.objects.filter(user=request.user, is_default=True).exclude(pk=getattr(address, "pk", None)).exists()
                obj.is_default = should_default
                if should_default:
                    CustomerAddress.objects.filter(user=request.user, is_default=True).exclude(pk=getattr(address, "pk", None)).update(is_default=False)
                obj.save()
                _audit(request.user, "address_saved", obj, "Address record created or updated")
            messages.success(request, "Address saved.")
            return redirect("profile_addresses")
    else:
        form = CustomerAddressForm(instance=address)
    context.update({"form": form, "address": address, "page_heading": "Edit address" if address else "Add address"})
    return render(request, "profiles/address_form.html", context)


@login_required
@require_POST
def address_delete(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    was_default = address.is_default
    address_id = address.pk
    with transaction.atomic():
        address.delete()
        if was_default:
            next_address = CustomerAddress.objects.filter(user=request.user).order_by("-updated_at").first()
            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=["is_default", "updated_at"])
        _audit(request.user, "address_deleted", f"CustomerAddress#{address_id}", "User removed an address")
    messages.success(request, "Address deleted.")
    return redirect("profile_addresses")


@login_required
@require_POST
def address_default(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    with transaction.atomic():
        CustomerAddress.objects.filter(user=request.user, is_default=True).exclude(pk=address.pk).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
        _audit(request.user, "address_default_changed", address, "User changed their default address")
    messages.success(request, "Default address updated.")
    return redirect("profile_addresses")


@login_required
def profile_preferences(request):
    context = _role_context(request.user)
    if request.method == "POST":
        form = ProfilePreferencesForm(request.POST, request.FILES, instance=context["prefs"])
        if form.is_valid():
            prefs = form.save()
            _audit(request.user, "profile_preferences_updated", request.user, "Profile preferences updated")
            messages.success(request, "Your preferences have been saved.")
            return redirect("profile_preferences")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProfilePreferencesForm(instance=context["prefs"])
    context["form"] = form
    return render(request, "profiles/preferences.html", context)


@login_required
def profile_security(request):
    context = _role_context(request.user)
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            _audit(user, "password_changed", user, "Password changed through authenticated profile security page")
            messages.success(request, "Your password has been changed. You remain signed in on this device.")
            return redirect("profile_security")
        messages.error(request, "Please correct the password errors below.")
    else:
        form = PasswordChangeForm(user=request.user)
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")
        field.widget.attrs.setdefault("autocomplete", "current-password")
    if "new_password1" in form.fields:
        form.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
    if "new_password2" in form.fields:
        form.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"
    context.update({"form": form, "deletion_request": AccountDeletionRequest.objects.filter(user=request.user).first()})
    return render(request, "profiles/security.html", context)


@login_required
def avatar_image(request):
    """Serve the signed-in user's own avatar; never expose a guessed public media path."""
    prefs = _preferences_for(request.user)
    if not prefs.avatar:
        raise Http404("No profile picture is set.")
    try:
        avatar_file = prefs.avatar.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Profile picture is unavailable.")
    suffix = prefs.avatar.name.rsplit(".", 1)[-1].lower()
    content_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    response = FileResponse(avatar_file, content_type=content_types.get(suffix, "application/octet-stream"))
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def remove_avatar(request):
    prefs = _preferences_for(request.user)
    if prefs.avatar:
        prefs.avatar.delete(save=True)
        _audit(request.user, "profile_avatar_removed", request.user, "Profile avatar removed")
        messages.success(request, "Your profile picture has been removed.")
    else:
        messages.info(request, "There is no profile picture to remove.")
    return redirect("profile_edit")


@login_required
def export_data(request):
    context = _role_context(request.user)
    user = request.user
    data = {
        "exported_at": timezone.now().isoformat(),
        "account": {
            "username": user.get_username(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            "role": context["role_label"],
            "personal_phone": context["prefs"].contact_phone,
            "date_of_birth": context["prefs"].date_of_birth.isoformat() if context["prefs"].date_of_birth else None,
            "preferred_language": context["prefs"].preferred_language,
            "preferred_fulfilment": context["prefs"].preferred_fulfilment,
        },
        "addresses": list(CustomerAddress.objects.filter(user=user).values(
            "recipient_name", "phone", "address_line1", "locality", "city", "state", "pincode", "address_type", "is_default"
        )),
        "orders": list(_customer_orders(user).values("reference", "status", "fulfilment", "total", "created_at")),
        "prescriptions": list(Prescription.objects.filter(owner=user).values("id", "status", "review_note", "created_at")),
        "owned_pharmacies": list(Pharmacy.objects.filter(owner=user).values("name", "verification_status", "city", "pincode")),
        "note": "This export includes metadata and does not include the contents of prescription files.",
    }
    response = JsonResponse(data, json_dumps_params={"indent": 2}, ensure_ascii=False)
    response["Content-Disposition"] = 'attachment; filename="medmitra-account-export.json"'
    response["Cache-Control"] = "private, no-store"
    _audit(user, "account_data_exported", user, "User downloaded their account data export")
    return response


@login_required
@require_POST
def delete_request(request):
    if request.POST.get("confirm") != "on":
        messages.error(request, "Please confirm that you understand this is a deletion request for review.")
        return redirect("profile_security")
    form = DeletionRequestForm(request.POST)
    if form.is_valid():
        existing = AccountDeletionRequest.objects.filter(user=request.user).first()
        if existing and existing.status in {AccountDeletionRequest.Status.PENDING, AccountDeletionRequest.Status.IN_REVIEW}:
            messages.info(request, "You already have an account deletion request awaiting review.")
        else:
            obj = existing or form.save(commit=False)
            obj.user = request.user
            obj.reason = form.cleaned_data.get("reason", "")
            obj.status = AccountDeletionRequest.Status.PENDING
            obj.reviewed_by = None
            obj.reviewed_at = None
            obj.save()
            _audit(request.user, "account_deletion_requested", obj, "User submitted an account deletion request for administrator review")
            messages.success(request, "Your account deletion request has been submitted. Your account has not been deleted; an administrator must review it.")
    else:
        messages.error(request, "Please add a valid request reason or confirm the request.")
    return redirect("profile_security")


@login_required
def saved_items(request):
    """Show only the signed-in user's saved medicines and verified pharmacies."""
    context = _role_context(request.user)
    context["saved_pharmacies"] = SavedPharmacy.objects.filter(user=request.user).select_related("pharmacy")
    context["saved_medicines"] = SavedMedicine.objects.filter(user=request.user).select_related("product")
    return render(request, "profiles/saved_items.html", context)


def _safe_return_url(request, fallback):
    from django.utils.http import url_has_allowed_host_and_scheme
    candidate = request.POST.get("next", "")
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return fallback


@login_required
@require_POST
def save_pharmacy(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)
    saved = SavedPharmacy.objects.filter(user=request.user, pharmacy=pharmacy).first()
    if saved:
        # Let users remove a previously saved pharmacy even if it later becomes suspended.
        saved.delete()
        messages.success(request, "Pharmacy removed from your saved list.")
        _audit(request.user, "pharmacy_unsaved", pharmacy, "User removed a saved pharmacy")
    elif pharmacy.verification_status == Pharmacy.VerificationStatus.APPROVED:
        SavedPharmacy.objects.get_or_create(user=request.user, pharmacy=pharmacy)
        messages.success(request, "Pharmacy saved to your list.")
        _audit(request.user, "pharmacy_saved", pharmacy, "User saved a verified pharmacy")
    else:
        messages.error(request, "Only currently verified pharmacies can be added to your saved list.")
    return redirect(_safe_return_url(request, reverse("profile_saved_items")))


@login_required
@require_POST
def save_medicine(request, pk):
    product = get_object_or_404(MedicineProduct, pk=pk)
    saved = SavedMedicine.objects.filter(user=request.user, product=product).first()
    if saved:
        # Existing saved rows can always be removed even if the catalogue entry is deactivated.
        saved.delete()
        messages.success(request, "Medicine removed from your saved list.")
        _audit(request.user, "medicine_unsaved", product, "User removed a saved medicine")
    elif product.active:
        SavedMedicine.objects.get_or_create(user=request.user, product=product)
        messages.success(request, "Medicine saved to your list. This does not create an order or recommend a substitute.")
        _audit(request.user, "medicine_saved", product, "User saved a medicine listing")
    else:
        messages.error(request, "Inactive catalogue products cannot be newly saved.")
    return redirect(_safe_return_url(request, reverse("profile_saved_items")))
