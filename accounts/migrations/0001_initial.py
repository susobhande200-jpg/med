import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="PatientProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("phone", models.CharField(blank=True, max_length=25)),
            ("date_of_birth", models.DateField(blank=True, null=True)),
            ("emergency_contact", models.CharField(blank=True, max_length=120)),
            ("email_verified", models.BooleanField(default=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="patient_profile", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="StaffProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("doctor", "Doctor"), ("receptionist", "Receptionist")], max_length=20)),
            ("phone", models.CharField(blank=True, max_length=25)),
            ("is_approved", models.BooleanField(default=False)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="staff_profile", to=settings.AUTH_USER_MODEL)),
        ]),
    ]
