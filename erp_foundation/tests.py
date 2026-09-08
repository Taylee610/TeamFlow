from datetime import timedelta
from io import StringIO, BytesIO
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings, TransactionTestCase
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone
from rest_framework.test import APITestCase

from projects.models import Project, Task
from chat.models import Conversation, ConversationParticipant, Message
from chat.permissions import can_access_conversation
from accounts.permissions import can_view_project
from .models import Membership, WorkspaceInvitation
from .services import create_workspace
from .testing import add_member

User = get_user_model()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WorkspaceIsolationTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', password='pass', role='admin')
        self.bob = User.objects.create_user(email='bob@example.com', password='pass', role='admin')
        self.a = create_workspace(self.alice, 'Alpha')
        self.b = create_workspace(self.bob, 'Beta')
        self.project = Project.objects.create(tenant=self.b, owner=self.bob, name='Private')
        self.task = Task.objects.create(project=self.project, title='Confidential')
        self.conversation = Conversation.objects.create(tenant=self.b, type='support')
        self.client.force_authenticate(self.alice)

    def test_global_admin_cannot_access_another_workspace(self):
        for path in (f'/api/projects/{self.project.pk}/', f'/api/tasks/{self.task.pk}/',
                     f'/api/chat/conversations/{self.conversation.pk}/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
        self.assertFalse(can_view_project(self.alice, self.project))
        self.assertFalse(can_access_conversation(self.alice, self.conversation))

    def test_forged_workspace_header_denied(self):
        self.assertEqual(self.client.get('/api/projects/', HTTP_X_WORKSPACE_ID=str(self.b.pk)).status_code, 403)

    def test_multi_membership_requires_selection_and_respects_it(self):
        add_member(self.b, self.alice)
        self.assertEqual(self.client.get('/api/projects/').status_code, 400)
        response = self.client.get('/api/projects/', HTTP_X_WORKSPACE_ID=str(self.b.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'], [])

    def test_suspended_membership_or_tenant_denied(self):
        membership = Membership.objects.get(tenant=self.a, user=self.alice)
        membership.is_active = False; membership.save()
        self.assertEqual(self.client.get('/api/projects/').status_code, 403)
        membership.is_active = True; membership.save()
        self.a.is_active = False; self.a.save()
        self.assertEqual(self.client.get('/api/v1/erp/accounts/').status_code, 403)

    def test_mismatched_role_tenant_denied(self):
        membership = Membership.objects.get(tenant=self.a, user=self.alice)
        membership.role = Membership.objects.get(tenant=self.b, user=self.bob).role
        membership.save()
        self.assertEqual(self.client.get('/api/projects/').status_code, 403)

    def test_unmapped_legacy_project_is_hidden(self):
        legacy = Project.objects.create(owner=self.alice, name='Legacy')
        self.assertEqual(self.client.get(f'/api/projects/{legacy.pk}/').status_code, 404)

    def test_new_project_uses_selected_workspace(self):
        response = self.client.post('/api/projects/', {'name': 'Delivery', 'tenant': self.b.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Project.objects.get(pk=response.data['id']).tenant_id, self.a.pk)
        self.assertTrue(response.data['can_manage'])

    def test_cross_workspace_chat_members_and_project_are_rejected(self):
        for payload in ({'type': 'dm', 'member_ids': [self.bob.pk]},
                        {'type': 'channel', 'name': 'Leak', 'project': self.project.pk}):
            self.assertEqual(self.client.post('/api/chat/conversations/', payload, format='json').status_code, 400)

    def test_support_only_available_to_admin_or_assigned_member(self):
        member = User.objects.create_user(email='member@example.com', password='pass')
        add_member(self.b, member)
        self.client.force_authenticate(member)
        self.assertEqual(self.client.get(f'/api/chat/conversations/{self.conversation.pk}/').status_code, 404)
        self.conversation.assigned_agent = member; self.conversation.save()
        self.assertEqual(self.client.get(f'/api/chat/conversations/{self.conversation.pk}/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/chat/conversations/{self.conversation.pk}/assign/').status_code, 403)

    def test_reply_cannot_reference_another_conversation(self):
        channel = Conversation.objects.create(tenant=self.a, type='channel')
        ConversationParticipant.objects.create(conversation=channel, user=self.alice)
        private = Message.objects.create(conversation=self.conversation, sender=self.bob, body='Private')
        response = self.client.post(f'/api/chat/conversations/{channel.pk}/messages/', {'body': 'reply', 'parent': private.pk})
        self.assertEqual(response.status_code, 400)

    def test_realtime_access_is_revoked_with_membership(self):
        channel = Conversation.objects.create(tenant=self.b, type='channel')
        ConversationParticipant.objects.create(conversation=channel, user=self.bob)
        self.assertTrue(can_view_project(self.bob, self.project))
        self.assertTrue(can_access_conversation(self.bob, channel))
        Membership.objects.filter(tenant=self.b, user=self.bob).update(is_active=False)
        self.assertFalse(can_view_project(self.bob, self.project))
        self.assertFalse(can_access_conversation(self.bob, channel))

    def test_private_files_require_authorization(self):
        self.task.attachment = 'task_files/secret.txt'; self.task.save()
        self.assertEqual(self.client.get(f'/api/files/tasks/{self.task.pk}/').status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/files/tasks/{self.task.pk}/').status_code, 401)
        self.assertEqual(self.client.get('/media/task_files/secret.txt').status_code, 404)
        self.client.force_authenticate(self.bob)
        with patch('django.db.models.fields.files.FieldFile.open', return_value=BytesIO(b'secret')):
            response = self.client.get(f'/api/files/tasks/{self.task.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'secret')

    def test_mapping_is_explicit_dry_run_and_validates_memberships(self):
        project = Project.objects.create(owner=self.alice, name='Legacy')
        call_command('map_workspace_records', tenant=self.a.pk, projects=[project.pk], stdout=StringIO())
        project.refresh_from_db(); self.assertIsNone(project.tenant_id)
        call_command('map_workspace_records', tenant=self.a.pk, projects=[project.pk], apply=True, stdout=StringIO())
        project.refresh_from_db(); self.assertEqual(project.tenant_id, self.a.pk)
        with self.assertRaises(CommandError):
            call_command('map_workspace_records', tenant=self.b.pk, projects=[project.pk], apply=True, stdout=StringIO())


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WorkspaceOnboardingTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass')
        self.guest = User.objects.create_user(email='guest@example.com', password='pass')
        self.tenant = create_workspace(self.owner, 'Team')
        self.client.force_authenticate(self.owner)

    def invitation(self):
        response = self.client.post('/api/workspaces/invitations/', {'email': self.guest.email})
        self.assertEqual(response.status_code, 201)
        return parse_qs(urlparse(response.data['invite_url']).query)['invite'][0]

    def test_create_workspace_and_first_project(self):
        self.client.force_authenticate(self.guest)
        response = self.client.post('/api/workspaces/', {'name': 'A business name longer than seventeen characters'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['role'], 'admin')
        membership = Membership.objects.get(user=self.guest)
        self.assertLessEqual(len(membership.tenant.slug), 50)
        self.assertEqual(self.client.post('/api/projects/', {'name': 'First delivery'}).status_code, 201)

    def test_invitation_acceptance_is_bound_to_email_and_one_use(self):
        token = self.invitation()
        self.assertNotEqual(WorkspaceInvitation.objects.get().token_digest, token)
        self.assertEqual(self.client.post('/api/workspaces/invitations/accept/', {'token': token}).status_code, 403)
        self.client.force_authenticate(self.guest)
        response = self.client.post('/api/workspaces/invitations/accept/', {'token': token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'member')
        self.assertEqual(self.client.post('/api/workspaces/invitations/accept/', {'token': token}).status_code, 403)
        self.assertEqual(self.client.post('/api/workspaces/invitations/', {'email': 'next@example.com'}).status_code, 403)

    def test_expired_revoked_and_suspended_invitations_denied(self):
        token = self.invitation()
        invitation = WorkspaceInvitation.objects.get()
        self.client.force_authenticate(self.guest)
        invitation.expires_at = timezone.now() - timedelta(seconds=1); invitation.save()
        self.assertEqual(self.client.post('/api/workspaces/invitations/accept/', {'token': token}).status_code, 403)
        invitation.expires_at = timezone.now() + timedelta(days=1)
        invitation.revoked_at = timezone.now(); invitation.save()
        self.assertEqual(self.client.post('/api/workspaces/invitations/accept/', {'token': token}).status_code, 403)
        invitation.revoked_at = None; invitation.save()
        membership = add_member(self.tenant, self.guest)
        membership.is_active = False; membership.save()
        self.assertEqual(self.client.post('/api/workspaces/invitations/accept/', {'token': token}).status_code, 403)

    def test_profile_cannot_change_email_to_capture_an_invitation(self):
        self.client.patch('/api/auth/me/', {'email': self.guest.email})
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, 'owner@example.com')

    def test_owner_can_revoke_invitation_before_acceptance(self):
        token = self.invitation()
        invitation = WorkspaceInvitation.objects.get()
        self.assertEqual(self.client.delete(f'/api/workspaces/invitations/{invitation.pk}/').status_code, 204)
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.post('/api/workspaces/invitations/accept/', {'token': token}).status_code, 403)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class WorkspaceSocketTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass')
        self.outsider = User.objects.create_user(email='outsider@example.com', password='pass', role='admin')
        self.tenant = create_workspace(self.owner, 'Team')
        self.project = Project.objects.create(tenant=self.tenant, owner=self.owner, name='Private')
        self.conversation = Conversation.objects.create(tenant=self.tenant, type='support')

    def test_project_and_chat_sockets_reject_outsiders_and_anonymous(self):
        from teamtaskmanager.asgi import application
        token = str(AccessToken.for_user(self.outsider))

        async def scenario():
            for path in (f'/ws/projects/{self.project.pk}/', f'/ws/chat/conversations/{self.conversation.pk}/'):
                for suffix in ('', f'?token={token}'):
                    socket = WebsocketCommunicator(application, path + suffix)
                    connected, _ = await socket.connect()
                    self.assertFalse(connected)
                    await socket.disconnect()
        async_to_sync(scenario)()

    def test_project_socket_closes_after_membership_revocation(self):
        from teamtaskmanager.asgi import application
        token = str(AccessToken.for_user(self.owner))

        async def scenario():
            socket = WebsocketCommunicator(application, f'/ws/projects/{self.project.pk}/?token={token}')
            connected, _ = await socket.connect()
            self.assertTrue(connected)
            await database_sync_to_async(Membership.objects.filter(tenant=self.tenant, user=self.owner).update)(is_active=False)
            await get_channel_layer().group_send(f'project_{self.project.pk}', {'type': 'task_update', 'title': 'Private'})
            event = await socket.receive_output()
            self.assertEqual(event['type'], 'websocket.close')
            await socket.disconnect()
        async_to_sync(scenario)()
