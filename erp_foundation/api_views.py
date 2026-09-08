import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import UserSerializer
from .access import active_memberships, workspace_membership, can_admin_workspace
from .models import Membership, WorkspaceInvitation
from .services import create_workspace, workspace_roles


def workspace_data(membership):
    return {'id': membership.tenant_id, 'name': membership.tenant.name,
            'role': 'admin' if can_admin_workspace(membership) else 'member'}


class WorkspaceInput(serializers.Serializer):
    name = serializers.CharField(max_length=180)


class InviteInput(serializers.Serializer):
    email = serializers.EmailField()


class AcceptInput(serializers.Serializer):
    token = serializers.CharField(max_length=128)


class WorkspacesView(APIView):
    def get(self, request):
        return Response([workspace_data(m) for m in active_memberships(request.user).order_by('tenant_id')])

    def post(self, request):
        serializer = WorkspaceInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = create_workspace(request.user, serializer.validated_data['name'])
        return Response(workspace_data(active_memberships(request.user).get(tenant=tenant)), status=201)


class WorkspaceMembersView(APIView):
    def get(self, request):
        membership = workspace_membership(request)
        members = Membership.objects.filter(tenant=membership.tenant, is_active=True, user__is_active=True).select_related('user', 'role', 'tenant')
        return Response([{'id': m.pk, 'user': UserSerializer(m.user).data,
                          'role': 'admin' if can_admin_workspace(m) else 'member'} for m in members])


class InvitationsView(APIView):
    def get(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Only workspace administrators can view invitations.')
        return Response(list(WorkspaceInvitation.objects.filter(
            tenant=membership.tenant, accepted_at__isnull=True, revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').values('id', 'email', 'expires_at')))

    def post(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Only workspace administrators can invite teammates.')
        serializer = InviteInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = secrets.token_urlsafe(32)
        invitation = WorkspaceInvitation.objects.create(
            tenant=membership.tenant, email=serializer.validated_data['email'].lower(),
            token_digest=hashlib.sha256(token.encode()).hexdigest(), created_by=request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )
        # Return once to the administrator for sharing. Never persist the bearer token.
        return Response({'id': invitation.pk, 'email': invitation.email,
                         'expires_at': invitation.expires_at,
                         'invite_url': f'{settings.FRONTEND_URL.rstrip("/")}/workspaces?invite={token}'}, status=201)


class RevokeInvitationView(APIView):
    @transaction.atomic
    def delete(self, request, pk):
        from django.shortcuts import get_object_or_404
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Only workspace administrators can revoke invitations.')
        invitation = get_object_or_404(WorkspaceInvitation.objects.select_for_update(),
                                     pk=pk, tenant=membership.tenant, accepted_at__isnull=True)
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=['revoked_at'])
        return Response(status=204)


class AcceptInvitationView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = AcceptInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        digest = hashlib.sha256(serializer.validated_data['token'].encode()).hexdigest()
        invitation = WorkspaceInvitation.objects.select_for_update().filter(
            token_digest=digest, tenant__is_active=True, revoked_at__isnull=True,
            accepted_at__isnull=True, expires_at__gt=timezone.now(),
        ).select_related('tenant').first()
        if not invitation or invitation.email.casefold() != request.user.email.casefold():
            raise PermissionDenied('Invitation is invalid, expired, or belongs to another email address.')
        existing = Membership.objects.filter(tenant=invitation.tenant, user=request.user).first()
        if existing and not existing.is_active:
            raise PermissionDenied('Your workspace access has been suspended. Contact its administrator.')
        _, role = workspace_roles(invitation.tenant)
        membership, _ = Membership.objects.get_or_create(
            tenant=invitation.tenant, user=request.user, defaults={'role': role},
        )
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted_at'])
        return Response(workspace_data(membership))
