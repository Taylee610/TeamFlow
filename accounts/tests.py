from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class UserRoleTests(APITestCase):
    def test_default_role_is_member(self):
        user = User.objects.create_user(email='test@example.com', password='pass123')
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertFalse(user.is_admin)

    def test_signup_cannot_set_role(self):
        response = self.client.post('/api/auth/signup/', {
            'email': 'newuser@example.com',
            'password': 'StrongPass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'admin',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.role, User.Role.MEMBER)

    def test_me_endpoint_includes_role(self):
        user = User.objects.create_user(email='test@example.com', password='pass123', role=User.Role.MANAGER)
        self.client.force_authenticate(user)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'manager')
