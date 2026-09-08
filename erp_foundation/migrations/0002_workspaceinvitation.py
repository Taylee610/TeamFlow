import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('erp_foundation', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [migrations.CreateModel(
        name='WorkspaceInvitation',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('email', models.EmailField(max_length=254)),
            ('token_digest', models.CharField(max_length=64, unique=True)),
            ('expires_at', models.DateTimeField()),
            ('accepted_at', models.DateTimeField(blank=True, null=True)),
            ('revoked_at', models.DateTimeField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='erp_foundation.tenant')),
        ],
    )]
