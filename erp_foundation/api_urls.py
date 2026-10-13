from django.urls import path
from .api_views import WorkspacesView, WorkspaceMembersView, InvitationsView, AcceptInvitationView, RevokeInvitationView
from .api_views import RolesView, MemberAccessView

urlpatterns = [
    path('', WorkspacesView.as_view()),
    path('members/', WorkspaceMembersView.as_view()),
    path('members/<int:pk>/', MemberAccessView.as_view()),
    path('roles/', RolesView.as_view()),
    path('invitations/', InvitationsView.as_view()),
    path('invitations/accept/', AcceptInvitationView.as_view()),
    path('invitations/<int:pk>/', RevokeInvitationView.as_view()),
]
