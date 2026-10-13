from urllib.parse import urlparse, parse_qs
from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from workspace_tools.models import Job

User=get_user_model()


class RecoveryTests(APITestCase):
    def setUp(self):
        self.user=User.objects.create_user(email='recover@example.com',password='Old-password-738!')

    def test_reset_neutral_response_and_single_use(self):
        known=self.client.post('/api/auth/password/reset/',{'email':self.user.email})
        unknown=self.client.post('/api/auth/password/reset/',{'email':'missing@example.com'})
        self.assertEqual(known.data,unknown.data)
        body=Job.objects.get(kind='email').payload['body']
        link=next(line for line in body.splitlines() if '/account/reset?' in line)
        params=parse_qs(urlparse(link).query)
        data={'uid':params['uid'][0],'token':params['token'][0],'password':'New-password-947!'}
        self.assertEqual(self.client.post('/api/auth/password/confirm/',data).status_code,200)
        self.assertEqual(self.client.post('/api/auth/password/confirm/',data).status_code,400)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password(data['password']))

    def test_email_verification_cannot_change_identity(self):
        token=signing.dumps({'user':self.user.pk,'email':self.user.email},salt='email-verification')
        self.assertEqual(self.client.post('/api/auth/email/verify/',{'token':token}).status_code,200)
        self.user.refresh_from_db();self.assertTrue(self.user.email_verified)
        self.assertEqual(self.client.post('/api/auth/email/verify/',{'token':token+'tamper'}).status_code,400)

    def test_logout_blacklists_refresh(self):
        token=str(RefreshToken.for_user(self.user))
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/auth/logout/',{'refresh':token}).status_code,204)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/auth/token/refresh/',{'refresh':token}).status_code,401)
