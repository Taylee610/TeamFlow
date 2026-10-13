from django.urls import path

from .api_views import SignupView, MeView
from .recovery import ResetRequestView, ResetConfirmView, VerificationRequestView, VerificationConfirmView, LogoutView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('me/', MeView.as_view(), name='me'),
    path('password/reset/', ResetRequestView.as_view()),
    path('password/confirm/', ResetConfirmView.as_view()),
    path('email/request/', VerificationRequestView.as_view()),
    path('email/verify/', VerificationConfirmView.as_view()),
    path('logout/', LogoutView.as_view()),
]
