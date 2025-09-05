from django.shortcuts import redirect

def landing_redirect(request):
    """
    Redirect users depending on authentication status:
    - Authenticated users → project list (dashboard)
    - Unauthenticated users → login page
    """
    if request.user.is_authenticated:
        return redirect('project-list')  # your ProjectListView URL
    return redirect('login')  # Django's login page
