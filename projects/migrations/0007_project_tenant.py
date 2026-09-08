import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('erp_foundation', '0002_workspaceinvitation'),
        ('projects', '0006_task_labels_task_linked_tasks_task_parent_and_more'),
    ]
    operations = [migrations.AddField(
        model_name='project', name='tenant',
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='projects', to='erp_foundation.tenant'),
    )]
