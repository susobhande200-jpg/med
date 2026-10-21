from django.contrib import admin
from .models import PatientProfile, StaffProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "email_verified", "created_at")
    search_fields = ("user__username", "user__email")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_approved")
    list_filter = ("role", "is_approved")
    search_fields = ("user__username", "user__email")
