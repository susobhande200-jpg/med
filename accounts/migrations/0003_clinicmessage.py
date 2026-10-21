import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('accounts','0002_staff_roles'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name='ClinicMessage',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('body',models.TextField(max_length=3000)),('created_at',models.DateTimeField(auto_now_add=True)),('read_at',models.DateTimeField(blank=True,null=True)),('recipient',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='clinic_messages_received',to=settings.AUTH_USER_MODEL)),('sender',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='clinic_messages_sent',to=settings.AUTH_USER_MODEL))],options={'ordering':['created_at']})]
