from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0001_initial"),
        ("marketplace", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedPharmacy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("pharmacy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by_users", to="marketplace.pharmacy")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_pharmacy_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="savedpharmacy",
            constraint=models.UniqueConstraint(fields=("user", "pharmacy"), name="uniq_saved_user_pharmacy"),
        ),
        migrations.CreateModel(
            name="SavedMedicine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by_users", to="marketplace.medicineproduct")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_medicine_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="savedmedicine",
            constraint=models.UniqueConstraint(fields=("user", "product"), name="uniq_saved_user_medicine"),
        ),
    ]
