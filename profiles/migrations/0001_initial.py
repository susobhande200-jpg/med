# Generated as the initial migration for the optional MediSearch profile add-on.
import profiles.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ProfilePreferences",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("avatar", models.ImageField(blank=True, upload_to=profiles.models.profile_avatar_path)),
                ("contact_phone", models.CharField(blank=True, max_length=25)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("preferred_language", models.CharField(choices=[("en", "English"), ("bn", "বাংলা (Bengali)"), ("hi", "हिन्दी (Hindi)")], default="en", max_length=8)),
                ("preferred_fulfilment", models.CharField(choices=[("delivery", "Home delivery"), ("pickup", "Pharmacy pickup")], default="pickup", max_length=12)),
                ("notify_order_updates", models.BooleanField(default=True)),
                ("notify_prescription_updates", models.BooleanField(default=True)),
                ("notify_inventory_alerts", models.BooleanField(default=True)),
                ("notify_promotions", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Profile and preferences", "verbose_name_plural": "Profiles and preferences"},
        ),
        migrations.CreateModel(
            name="CustomerAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=25)),
                ("address_line1", models.CharField(help_text="House number, street or building", max_length=180)),
                ("locality", models.CharField(blank=True, max_length=120)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(default="West Bengal", max_length=100)),
                ("pincode", models.CharField(db_index=True, max_length=10)),
                ("address_type", models.CharField(choices=[("home", "Home"), ("work", "Work"), ("other", "Other")], default="home", max_length=10)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profile_addresses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-is_default", "-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="customeraddress",
            index=models.Index(fields=["user", "is_default"], name="prof_addr_user_default_idx"),
        ),
        migrations.CreateModel(
            name="AccountDeletionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, max_length=300)),
                ("status", models.CharField(choices=[("pending", "Pending review"), ("in_review", "In review"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=16)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profile_deletion_reviews", to=settings.AUTH_USER_MODEL)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile_deletion_request", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-requested_at"], "verbose_name": "Account deletion request", "verbose_name_plural": "Account deletion requests"},
        ),
    ]
