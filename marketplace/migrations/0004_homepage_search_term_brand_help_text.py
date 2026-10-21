from django.db import migrations, models
import marketplace.models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0003_footer_social_link"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepagesearchterm",
            name="target_url",
            field=models.CharField(
                blank=True,
                help_text="Optional internal path or absolute HTTP(S) destination. Otherwise, this term searches MedMitra.",
                max_length=500,
                validators=[marketplace.models.validate_homepage_link],
            ),
        ),
    ]
