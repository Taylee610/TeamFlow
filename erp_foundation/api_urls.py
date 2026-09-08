from django.urls import path
from .api_views import WorkspacesView, WorkspaceMembersView, InvitationsView, AcceptInvitationView, RevokeInvitationView

urlpatterns = [
    path('', WorkspacesView.as_view()),
    path('members/', WorkspaceMembersView.as_view()),
    path('invitations/', InvitationsView.as_view()),
    path('invitations/accept/', AcceptInvitationView.as_view()),
    path('invitations/<int:pk>/', RevokeInvitationView.as_view()),
]
