from django.db import connection
from django.http import JsonResponse


def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ready'})
