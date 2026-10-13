from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from workspace_tools.models import Job, MonitorCheck


class Command(BaseCommand):
    help='Remove completed delivery payloads older than 7 days and monitor samples older than 90 days.'

    def handle(self,*args,**options):
        jobs,_=Job.objects.filter(status='done',created_at__lt=timezone.now()-timedelta(days=7)).delete()
        checks,_=MonitorCheck.objects.filter(checked_at__lt=timezone.now()-timedelta(days=90)).delete()
        self.stdout.write(f'Removed {jobs} completed jobs and {checks} old samples. Failed jobs are retained for review.')
