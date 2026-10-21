from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.AlterField(
        model_name="staffprofile", name="role",
        field=models.CharField(max_length=20, choices=[("doctor", "Doctor"), ("receptionist", "Receptionist"), ("nurse", "Nurse / Medical Staff"), ("pharmacist", "Pharmacist")]),
    )]
