from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Contact, Conversation, ConversationParticipant
from erp_foundation.services import create_workspace
from erp_foundation.testing import add_member

User = get_user_model()


class HelpdeskTests(APITestCase):
    def setUp(self):
        self.agent = User.objects.create_user(email='agent@example.com', password='pass123')
        self.other_agent = User.objects.create_user(email='agent2@example.com', password='pass123')
        self.tenant = create_workspace(self.agent, 'Support')
        add_member(self.tenant, self.other_agent)
        self.contact = Contact.objects.create(name='Jane Customer', email='jane@customer.com', external_id='visitor-1')
        self.unassigned_convo = Conversation.objects.create(tenant=self.tenant, type=Conversation.SUPPORT, contact=self.contact)
        self.mine_convo = Conversation.objects.create(
            tenant=self.tenant, type=Conversation.SUPPORT, contact=self.contact, assigned_agent=self.agent
        )
        self.client.force_authenticate(self.agent)

    def test_unassigned_lists_only_unassigned_support_conversations(self):
        response = self.client.get('/api/chat/conversations/unassigned/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in response.data]
        self.assertIn(self.unassigned_convo.id, ids)
        self.assertNotIn(self.mine_convo.id, ids)

    def test_my_lists_only_conversations_assigned_to_me(self):
        response = self.client.get('/api/chat/conversations/my/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in response.data]
        self.assertEqual(ids, [self.mine_convo.id])

    def test_assign_defaults_to_self(self):
        response = self.client.post(f'/api/chat/conversations/{self.unassigned_convo.id}/assign/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unassigned_convo.refresh_from_db()
        self.assertEqual(self.unassigned_convo.assigned_agent, self.agent)

    def test_assign_to_specific_agent(self):
        response = self.client.post(
            f'/api/chat/conversations/{self.unassigned_convo.id}/assign/',
            {'agent_id': self.other_agent.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unassigned_convo.refresh_from_db()
        self.assertEqual(self.unassigned_convo.assigned_agent, self.other_agent)

    def test_assign_rejects_non_support_conversation(self):
        channel = Conversation.objects.create(tenant=self.tenant, type=Conversation.CHANNEL, name='general')
        ConversationParticipant.objects.create(conversation=channel, user=self.agent)
        response = self.client.post(f'/api/chat/conversations/{channel.id}/assign/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_updatable_via_patch(self):
        response = self.client.patch(
            f'/api/chat/conversations/{self.mine_convo.id}/', {'status': 'resolved'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mine_convo.refresh_from_db()
        self.assertEqual(self.mine_convo.status, Conversation.RESOLVED)
