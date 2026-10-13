from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help='Create and verify a database backup. PostgreSQL needs pg_dump installed.'

    def add_arguments(self,parser):
        parser.add_argument('--output',required=True,help='Backup directory. Backups contain private data.')

    def handle(self,*args,**options):
        target=Path(options['output']).resolve()
        target.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        database=settings.DATABASES['default']
        if database['ENGINE'].endswith('sqlite3'):
            if str(database['NAME'])==':memory:':raise CommandError('An in-memory database cannot be backed up with this command.')
            source=Path(database['NAME']).resolve()
            if not source.is_file():raise CommandError('Database does not exist.')
            output=target/f'teamflow-{stamp}.sqlite3'
            with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as original,sqlite3.connect(output) as backup:
                original.backup(backup)
                if backup.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise CommandError('Backup integrity check failed.')
        elif database['ENGINE'].endswith('postgresql'):
            output=target/f'teamflow-{stamp}.dump'
            environment=dict(os.environ,PGPASSWORD=database.get('PASSWORD',''))
            try:
                subprocess.run(['pg_dump','--format=custom','--host',database.get('HOST','localhost'),'--port',str(database.get('PORT',5432)),'--username',database['USER'],'--file',str(output),str(database['NAME'])],env=environment,check=True,capture_output=True)
                subprocess.run(['pg_restore','--list',str(output)],check=True,capture_output=True)
            except (OSError,subprocess.CalledProcessError):raise CommandError('PostgreSQL backup failed. Check client tools and connection configuration.')
        else:raise CommandError('Unsupported database backend.')
        self.stdout.write(str(output))
