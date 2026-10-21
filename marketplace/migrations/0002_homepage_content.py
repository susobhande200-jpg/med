# Admin-managed homepage content: banners, metrics, reviews, popular terms and SEO copy.
import django.core.validators
import marketplace.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomepageEditorialSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("eyebrow", models.CharField(blank=True, max_length=100)),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField(help_text="Plain text only; line breaks are displayed on the public homepage.")),
                ("seo_description", models.CharField(blank=True, help_text="Optional homepage meta description. First active entry with this value is used.", max_length=255)),
                ("button_label", models.CharField(blank=True, max_length=60)),
                ("button_url", models.CharField(blank=True, max_length=500, validators=[marketplace.models.validate_homepage_link])),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Homepage information / SEO section", "verbose_name_plural": "Homepage information / SEO sections", "ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="HomepagePromotion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("subtitle", models.CharField(blank=True, max_length=240)),
                ("image", models.ImageField(upload_to="homepage/promotions/")),
                ("alt_text", models.CharField(help_text="Describe the image for accessibility.", max_length=180)),
                ("target_url", models.CharField(blank=True, help_text="Optional internal path (e.g. /medicines/) or absolute HTTP(S) destination.", max_length=500, validators=[marketplace.models.validate_homepage_link])),
                ("button_label", models.CharField(blank=True, default="Explore offer", max_length=60)),
                ("starts_at", models.DateTimeField(blank=True, help_text="Optional scheduled start in the site's timezone.", null=True)),
                ("ends_at", models.DateTimeField(blank=True, help_text="Optional end time; the banner is hidden after this time.", null=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Homepage promotion / advertisement", "verbose_name_plural": "Homepage promotions / advertisements", "ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="HomepageSearchTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(choices=[("healthcare", "Top-selling healthcare products"), ("medicines", "Top-selling medicines"), ("searched", "Top-searched medicines"), ("vaccines", "Top-searched vaccines")], db_index=True, max_length=20)),
                ("term", models.CharField(max_length=150)),
                ("target_url", models.CharField(blank=True, help_text="Optional internal path or absolute HTTP(S) destination. Otherwise, this term searches MediSearch.", max_length=500, validators=[marketplace.models.validate_homepage_link])),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Homepage popular search term", "verbose_name_plural": "Homepage popular search terms", "ordering": ["section", "sort_order", "term"]},
        ),
        migrations.CreateModel(
            name="HomepageTestimonial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(max_length=100)),
                ("location_label", models.CharField(blank=True, max_length=100)),
                ("review_date", models.DateField(blank=True, null=True)),
                ("quote", models.TextField(max_length=1200)),
                ("rating", models.PositiveSmallIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("is_published", models.BooleanField(default=False, help_text="Only publish genuine reviews you are authorised to display.")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Homepage customer review", "verbose_name_plural": "Homepage customer reviews", "ordering": ["sort_order", "-review_date", "id"]},
        ),
        migrations.CreateModel(
            name="HomepageTrustMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(help_text="Use a real, supportable value (or a short label).", max_length=60)),
                ("label", models.CharField(max_length=100)),
                ("detail", models.CharField(blank=True, max_length=180)),
                ("icon", models.CharField(default="bi-shield-check", help_text="Bootstrap icon class, e.g. bi-shop.", max_length=50)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Homepage trust metric", "verbose_name_plural": "Homepage trust metrics", "ordering": ["sort_order", "id"]},
        ),
    ]
