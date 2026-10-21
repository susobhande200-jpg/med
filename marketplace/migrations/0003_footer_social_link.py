# Admin-managed social links for the public MediSearch footer.
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0002_homepage_content"),
    ]

    operations = [
        migrations.CreateModel(
            name="FooterSocialLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("instagram", "Instagram"), ("facebook", "Facebook"), ("youtube", "YouTube"), ("linkedin", "LinkedIn"), ("x", "X"), ("whatsapp", "WhatsApp"), ("telegram", "Telegram"), ("other", "Other")], max_length=20)),
                ("label", models.CharField(blank=True, help_text="Optional text shown beside the icon. If blank, the platform name is used.", max_length=80)),
                ("url", models.URLField(help_text="Public HTTP(S) profile or page URL. Script and data URLs are not allowed.", max_length=500, validators=[django.core.validators.URLValidator(schemes=["http", "https"])])),
                ("open_in_new_tab", models.BooleanField(default=True, help_text="Open this external link in a new browser tab.")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Footer social media link", "verbose_name_plural": "Footer social media links", "ordering": ["sort_order", "platform", "id"]},
        ),
    ]
