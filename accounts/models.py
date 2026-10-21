from django.conf import settings
from django.db import models

class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    phone = models.CharField(max_length=25, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.user.get_full_name() or self.user.username

class StaffProfile(models.Model):
    class Role(models.TextChoices):
        PHARMACIST = "pharmacist", "Pharmacist"
        STORE_MANAGER = "store_manager", "Store manager"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PHARMACIST)
    phone = models.CharField(max_length=25, blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
