from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from projects.models import Project
from chat.models import Conversation
from erp_foundation.models import Tenant, Membership


class Command(BaseCommand):
    help = 'Explicitly map legacy records to a workspace. Dry run by default; never grants memberships.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, required=True)
        parser.add_argument('--projects', type=int, nargs='*', default=[])
        parser.add_argument('--conversations', type=int, nargs='*', default=[])
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(pk=options['tenant'], is_active=True).first()
        if not tenant:
            raise CommandError('Active workspace not found.')
        active_ids = set(Membership.objects.filter(tenant=tenant, is_active=True, user__is_active=True,
                                                   role__tenant=tenant).values_list('user_id', flat=True))
        projects = list(Project.objects.select_for_update().filter(pk__in=options['projects']))
        conversations = list(Conversation.objects.select_for_update().filter(pk__in=options['conversations']))
        if len(projects) != len(set(options['projects'])) or len(conversations) != len(set(options['conversations'])):
            raise CommandError('One or more record IDs do not exist.')
        for project in projects:
            ids = {project.owner_id} | set(project.members.values_list('id', flat=True))
            ids |= set(project.tasks.exclude(assigned_to=None).values_list('assigned_to_id', flat=True))
            if project.tenant_id not in (None, tenant.pk) or not ids.issubset(active_ids):
                raise CommandError(f'Project {project.pk}: tenant conflict or users missing active workspace membership.')
        project_ids = {p.pk for p in projects}
        for conversation in conversations:
            ids = set(conversation.participants.values_list('user_id', flat=True))
            if conversation.assigned_agent_id:
                ids.add(conversation.assigned_agent_id)
            if conversation.tenant_id not in (None, tenant.pk) or not ids.issubset(active_ids):
                raise CommandError(f'Conversation {conversation.pk}: tenant conflict or missing memberships.')
            if conversation.project_id and conversation.project_id not in project_ids and conversation.project.tenant_id != tenant.pk:
                raise CommandError('Map the conversation project to the same workspace first or in this command.')
        if options['apply']:
            Project.objects.filter(pk__in=project_ids).update(tenant=tenant)
            Conversation.objects.filter(pk__in=[c.pk for c in conversations]).update(tenant=tenant)
        self.stdout.write(f'{"Mapped" if options["apply"] else "Validated (dry run)"}: {len(projects)} projects, {len(conversations)} conversations to workspace {tenant.pk}.')
