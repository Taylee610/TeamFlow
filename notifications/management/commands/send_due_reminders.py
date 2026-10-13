from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from projects.models import Task
from notifications.emails import send_due_date_reminder_email
from django.db import transaction
from workspace_tools.services import enqueue
from erp_foundation.access import active_memberships


class Command(BaseCommand):
    help = (
        "Emails assignees for tasks due within the next 24 hours that haven't "
        "had a reminder sent yet. Intended to be run periodically by an "
        "external scheduler (OS cron, Windows Task Scheduler, or your "
        "hosting platform's scheduled job) -- Django has no built-in cron."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        window_end = now + timedelta(hours=24)

        due_soon = Task.objects.exclude(status=Task.DONE).filter(
            due_date__isnull=False,
            due_date__gte=now,
            due_date__lte=window_end,
            reminder_sent_at__isnull=True,
            assigned_to__isnull=False,
        )

        sent = 0
        for task in due_soon:
            with transaction.atomic():
                task = Task.objects.select_for_update().select_related('project', 'assigned_to').get(pk=task.pk)
                if task.reminder_sent_at or task.status == Task.DONE or not task.assigned_to or not task.due_date or not now <= task.due_date <= window_end:
                    continue
                if not active_memberships(task.assigned_to).filter(tenant_id=task.project.tenant_id).exists():
                    continue
                enqueue('task_reminder', {'task': task.pk, 'assignee': task.assigned_to_id}, f'due-reminder:{task.pk}:{task.due_date.isoformat()}')
                task.reminder_sent_at = now
                task.save(update_fields=['reminder_sent_at'])
                sent += 1

        self.stdout.write(self.style.SUCCESS(f'Queued {sent} due-date reminder(s). Run the worker to deliver them.'))
