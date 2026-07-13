from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from projects.models import Task
from notifications.emails import send_due_date_reminder_email


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
            send_due_date_reminder_email(task)
            task.reminder_sent_at = now
            task.save(update_fields=['reminder_sent_at'])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Sent {sent} due-date reminder(s).'))
