import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from workspace_tools.services import run_one, schedule_monitors


class Command(BaseCommand):
    help = 'Process durable jobs and schedule website checks. Use --once for a bounded run.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                schedule_monitors()
                processed = 0
                while processed < options['limit'] and run_one():
                    processed += 1
                if options['once']:
                    self.stdout.write(f'Processed {processed} job(s).')
                    return
                time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write('Worker stopped.')
