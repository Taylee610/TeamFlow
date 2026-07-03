from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from tasks.models import Task

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user

    total_tasks = Task.objects.filter(user=user).count()
    todo = Task.objects.filter(user=user, status='TODO').count()
    in_progress = Task.objects.filter(user=user, status='IN_PROGRESS').count()
    done = Task.objects.filter(user=user, status='DONE').count()

    return Response({
        "total_tasks": total_tasks,
        "todo": todo,
        "in_progress": in_progress,
        "done": done
    })