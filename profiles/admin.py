from django.contrib import admin
from django.utils import timezone
from .models import AccountDeletionRequest, CustomerAddress, ProfilePreferences, SavedMedicine, SavedPharmacy


@admin.register(ProfilePreferences)
class ProfilePreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "contact_phone", "preferred_language", "updated_at")
    search_fields = ("user__username", "user__email", "contact_phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "user", "city", "pincode", "address_type", "is_default")
    search_fields = ("recipient_name", "user__username", "user__email", "city", "pincode")
    list_filter = ("address_type", "is_default", "state")


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "requested_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "requested_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "reason", "requested_at", "reviewed_by", "reviewed_at")

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = AccountDeletionRequest.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        if change and obj.status != AccountDeletionRequest.Status.PENDING and obj.reviewed_at is None:
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
        if change and old_status != obj.status:
            from marketplace.models import MarketplaceAuditLog
            MarketplaceAuditLog.objects.create(
                actor=request.user,
                action="account_deletion_reviewed",
                object_type="profiles.accountdeletionrequest",
                object_id=str(obj.pk),
                details=f"Deletion request status changed from {old_status or 'unknown'} to {obj.status}"[:500],
            )


@admin.register(SavedPharmacy)
class SavedPharmacyAdmin(admin.ModelAdmin):
    list_display = ("user", "pharmacy", "created_at")
    search_fields = ("user__username", "user__email", "pharmacy__name")
    readonly_fields = ("created_at",)


@admin.register(SavedMedicine)
class SavedMedicineAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__username", "user__email", "product__brand_name", "product__generic_name")
    readonly_fields = ("created_at",)
