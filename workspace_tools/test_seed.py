import tempfile
from io import StringIO
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from erp_foundation.services import create_workspace
from projects.models import Task
from accounting.models import JournalEntry, FinancialDocument
from workspace_tools.models import Form, Job
from workspace_tools.serializers import validate_fields


class PreviewSeedTests(TestCase):
    def test_offline_idempotent_balanced_seed(self):
        user = get_user_model().objects.create_user(email='preview@example.test', password='Test-pass-934!')
        tenant = create_workspace(user, 'Preview workspace')
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            args = {'workspace': tenant.pk, 'owner': user.email, 'stdout': StringIO()}
            call_command('seed_preview', **args)
            counts = (Task.objects.count(), FinancialDocument.objects.count(), JournalEntry.objects.count())
            call_command('seed_preview', **args)
            self.assertEqual(counts, (Task.objects.count(), FinancialDocument.objects.count(), JournalEntry.objects.count()))
            self.assertGreater(counts[0], 150)
            self.assertEqual(Job.objects.count(), 0)
            self.assertEqual(set(FinancialDocument.objects.values_list('status', flat=True)), {'draft', 'posted', 'partial', 'paid'})
            for journal in JournalEntry.objects.all(): self.assertEqual(journal.debit_total, journal.credit_total)
            for form in Form.objects.all(): validate_fields(form.fields)

    def test_refuse_customer_workspace(self):
        user = get_user_model().objects.create_user(email='customer@example.test', password='Test-pass-934!')
        tenant = create_workspace(user, 'Customer data')
        with self.assertRaises(CommandError): call_command('seed_preview', workspace=tenant.pk, owner=user.email)
