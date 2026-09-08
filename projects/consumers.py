# projects/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Project
from accounts.permissions import can_view_project

class ProjectTaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f"project_{self.project_id}"
        if not await self.can_access():
            await self.close(code=4003)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # receive broadcast from group
    async def task_update(self, event):
        if not await self.can_access():
            await self.close(code=4003)
            return
        await self.send(text_data=json.dumps({
            'task_id': event.get('task_id'),
            'title': event.get('title'),
            'status': event.get('status'),
            'project_id': event.get('project_id'),
        }))

    @database_sync_to_async
    def can_access(self):
        project = Project.objects.filter(pk=self.project_id).first()
        return bool(project and can_view_project(self.scope.get('user'), project))
