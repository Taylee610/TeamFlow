import tempfile
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken
from erp_foundation.services import create_workspace
from projects.models import Project
from .models import Client, ApprovalVersion
from .models import Job
from .services import run_one
from .quotas import stored_bytes


class SocketRevocationTests(TransactionTestCase):
    def test_password_change_closes_existing_project_socket(self):
        from teamtaskmanager.asgi import application
        User=get_user_model()
        user=User.objects.create_user(email='socket@example.com',password='old')
        tenant=create_workspace(user,'Socket')
        project=Project.objects.create(tenant=tenant,owner=user,name='Private')
        token=str(AccessToken.for_user(user))

        async def scenario():
            socket=WebsocketCommunicator(application,f'/ws/projects/{project.pk}/?token={token}')
            connected,_=await socket.connect()
            self.assertTrue(connected)
            await database_sync_to_async(User.objects.filter(pk=user.pk).update)(password=make_password('new'))
            await get_channel_layer().group_send(f'project_{project.pk}',{'type':'task_update','title':'Private'})
            output=await socket.receive_output()
            self.assertEqual(output['type'],'websocket.close')
            self.assertEqual(output['code'],4003)
            await socket.disconnect()
        async_to_sync(scenario)()


class ApprovalHistoryTests(APITestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        setting=override_settings(MEDIA_ROOT=directory.name)
        setting.enable();self.addCleanup(setting.disable)
        self.user=get_user_model().objects.create_user(email='approver@example.com',password='pass')
        self.tenant=create_workspace(self.user,'Approvals')
        self.client.force_authenticate(self.user)
        self.customer=Client.objects.create(tenant=self.tenant,created_by=self.user,name='Client')

    def test_replacing_approved_file_retains_version_and_storage_usage(self):
        first=b'version one'
        second=b'version two'
        response=self.client.post('/api/tools/approvals/',{'title':'Proof','client':self.customer.pk,'client_user':self.user.pk,'file':SimpleUploadedFile('one.txt',first)},format='multipart')
        self.assertEqual(response.status_code,201,response.data)
        pk=response.data['id']
        self.assertEqual(self.client.post(f'/api/tools/approvals/{pk}/decide/',{'version':1,'status':'approved','comment':'Looks good'}).status_code,200)
        response=self.client.patch(f'/api/tools/approvals/{pk}/',{'file':SimpleUploadedFile('two.txt',second)},format='multipart')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['version'],2)
        self.assertEqual(response.data['status'],'pending')
        self.assertEqual(ApprovalVersion.objects.get().status,'approved')
        self.assertEqual(stored_bytes(self.tenant),len(first)+len(second))
        self.assertEqual(self.client.post(f'/api/tools/approvals/{pk}/decide/',{'version':1,'status':'approved'}).status_code,400)

    def test_pending_private_email_is_suppressed_after_access_revocation(self):
        from erp_foundation.models import Membership
        from django.core import mail
        Job.objects.create(kind='email',dedup_key='guarded',payload={'to':self.user.email,'subject':'Private file','body':'Confidential',
                           'guard_user':self.user.pk,'guard_tenant':self.tenant.pk})
        Membership.objects.filter(tenant=self.tenant,user=self.user).update(is_active=False)
        self.assertTrue(run_one())
        self.assertEqual(len(mail.outbox),0)
