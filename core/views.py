from django.http import JsonResponse


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