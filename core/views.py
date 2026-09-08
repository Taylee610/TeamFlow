from django.http import JsonResponse
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from erp_foundation.access import workspace_membership
from accounts.permissions import can_view_project
from chat.permissions import can_access_conversation
from projects.models import Task
from chat.models import Message
from pathlib import PurePosixPath


class PrivateAttachmentView(APIView):
    def get(self, request, kind, pk):
        membership = workspace_membership(request)
        if kind == 'tasks':
            record = get_object_or_404(Task.objects.select_related('project'), pk=pk, project__tenant=membership.tenant)
            allowed = can_view_project(request.user, record.project)
        elif kind == 'messages':
            record = get_object_or_404(Message.objects.select_related('conversation'), pk=pk, conversation__tenant=membership.tenant)
            allowed = can_access_conversation(request.user, record.conversation)
        else:
            raise Http404
        if not allowed or not record.attachment:
            raise Http404
        try:
            response = FileResponse(record.attachment.open('rb'), as_attachment=True,
                                    filename=PurePosixPath(record.attachment.name).name)
        except FileNotFoundError:
            raise Http404
        response['Cache-Control'] = 'private, no-store'
        return response


def api_root(request):
    """Simple health-check / welcome response for the API root.

    Django serves the API only now -- the React app (in /src) is the UI
    and talks to these endpoints directly.
    """
    return JsonResponse({
        "status": "ok",
        "message": "TeamFlow API is running.",
        "docs": "/api/docs/",
        "schema": "/api/schema/",
    })
