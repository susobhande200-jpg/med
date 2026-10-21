from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pharmacy", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="medicinesale",
            name="patient_name",
            field=models.CharField(blank=True, max_length=160, verbose_name="Customer name"),
        ),
    ]
