from pathlib import Path
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def profile_avatar_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    return f"profile_avatars/user_{instance.user_id}/{uuid.uuid4().hex}{suffix}"


class ProfilePreferences(models.Model):
    """Supplemental personal details and preferences; existing User/profile models remain authoritative."""

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        BENGALI = "bn", "বাংলা (Bengali)"
        HINDI = "hi", "हिन्दी (Hindi)"

    class Fulfilment(models.TextChoices):
        DELIVERY = "delivery", "Home delivery"
        PICKUP = "pickup", "Pharmacy pickup"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_preferences")
    avatar = models.ImageField(upload_to=profile_avatar_path, blank=True)
    contact_phone = models.CharField(max_length=25, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    preferred_language = models.CharField(max_length=8, choices=Language.choices, default=Language.ENGLISH)
    preferred_fulfilment = models.CharField(max_length=12, choices=Fulfilment.choices, default=Fulfilment.PICKUP)
    notify_order_updates = models.BooleanField(default=True)
    notify_prescription_updates = models.BooleanField(default=True)
    notify_inventory_alerts = models.BooleanField(default=True)
    notify_promotions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profile and preferences"
        verbose_name_plural = "Profiles and preferences"

    def __str__(self):
        return f"Profile preferences for {self.user}"


class CustomerAddress(models.Model):
    class AddressType(models.TextChoices):
        HOME = "home", "Home"
        WORK = "work", "Work"
        OTHER = "other", "Other"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_addresses")
    recipient_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=25)
    address_line1 = models.CharField(max_length=180, help_text="House number, street or building")
    locality = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="West Bengal")
    pincode = models.CharField(max_length=10, db_index=True)
    address_type = models.CharField(max_length=10, choices=AddressType.choices, default=AddressType.HOME)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        indexes = [models.Index(fields=["user", "is_default"], name="prof_addr_user_default_idx")]

    def __str__(self):
        return f"{self.recipient_name} — {self.address_line1}, {self.city}"


class AccountDeletionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        IN_REVIEW = "in_review", "In review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_deletion_request")
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="profile_deletion_reviews")

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "Account deletion request"
        verbose_name_plural = "Account deletion requests"

    def __str__(self):
        return f"Deletion request for {self.user} ({self.status})"


class SavedPharmacy(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_pharmacy_items")
    pharmacy = models.ForeignKey("marketplace.Pharmacy", on_delete=models.CASCADE, related_name="saved_by_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "pharmacy"], name="uniq_saved_user_pharmacy")]

    def __str__(self):
        return f"{self.user} saved {self.pharmacy}"


class SavedMedicine(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_medicine_items")
    product = models.ForeignKey("marketplace.MedicineProduct", on_delete=models.CASCADE, related_name="saved_by_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="uniq_saved_user_medicine")]

    def __str__(self):
        return f"{self.user} saved {self.product}"
