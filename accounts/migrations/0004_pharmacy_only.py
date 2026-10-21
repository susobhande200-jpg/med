from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_clinicmessage")]

    operations = [
        migrations.DeleteModel(name="ClinicMessage"),
        migrations.AlterField(
            model_name="staffprofile",
            name="role",
            field=models.CharField(
                choices=[("pharmacist", "Pharmacist"), ("store_manager", "Store manager")],
                default="pharmacist",
                max_length=20,
            ),
        ),
    ]
