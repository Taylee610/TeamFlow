import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('chat', '0001_initial'), ('erp_foundation', '0002_workspaceinvitation')]
    operations = [migrations.AddField(
        model_name='conversation', name='tenant',
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='conversations', to='erp_foundation.tenant'),
    )]
