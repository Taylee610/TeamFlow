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
from workspace_tools.services import audit, enqueue
from .services import create_workspace, workspace_roles


def workspace_data(membership):
    return {'id': membership.tenant_id, 'name': membership.tenant.name,
            'role': 'admin' if can_admin_workspace(membership) else 'member',
            'role_name': membership.role.name,
            'permissions': list(membership.role.permissions.values_list('code', flat=True))}


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
        members = Membership.objects.filter(tenant=membership.tenant, user__is_active=True).select_related('user', 'role', 'tenant')
        if request.query_params.get('include_inactive') != 'true' or not can_admin_workspace(membership):
            members = members.filter(is_active=True)
        return Response([{'id': m.pk, 'user': UserSerializer(m.user).data,
                          'role': 'admin' if can_admin_workspace(m) else 'member', 'role_id': m.role_id, 'is_active': m.is_active,
                          'role_name': m.role.name, 'permissions': list(m.role.permissions.values_list('code', flat=True))} for m in members])


class InvitationsView(APIView):
    def get(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Only workspace administrators can view invitations.')
        return Response(list(WorkspaceInvitation.objects.filter(
            tenant=membership.tenant, accepted_at__isnull=True, revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').values('id', 'email', 'expires_at')))

    @transaction.atomic
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
        audit(invitation, request.user, 'invite', after={'email': invitation.email})
        invite_url = f'{settings.FRONTEND_URL.rstrip("/")}/workspaces?invite={token}'
        enqueue('email', {'to': invitation.email, 'subject': f'Invitation to {membership.tenant.name}',
                         'body': f'You have been invited to {membership.tenant.name}. Sign in or create an account using {invitation.email}, then open:\n{invite_url}\nThis invitation expires in 7 days.'}, f'invitation:{invitation.pk}')
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
        audit(invitation, request.user, 'revoke')
        return Response(status=204)


class AcceptInvitationView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = AcceptInput(data=request.data)
        if settings.REQUIRE_VERIFIED_EMAIL and not request.user.email_verified:
            raise PermissionDenied('Verify your email before accepting an invitation.')
        serializer.is_valid(raise_exception=True)
        digest = hashlib.sha256(serializer.validated_data['token'].encode()).hexdigest()
        invitation = WorkspaceInvitation.objects.select_for_update().filter(
            token_digest=digest, tenant__is_active=True, revoked_at__isnull=True,
            accepted_at__isnull=True, expires_at__gt=timezone.now(),
        ).select_related('tenant').first()
        if not invitation or invitation.email.casefold() != request.user.email.casefold():
            raise PermissionDenied('Invitation is invalid, expired, or belongs to another email address.')
        from .models import Tenant
        from workspace_tools.quotas import ensure_seat
        Tenant.objects.select_for_update().get(pk=invitation.tenant_id)
        existing = Membership.objects.filter(tenant=invitation.tenant, user=request.user).first()
        if existing and not existing.is_active:
            raise PermissionDenied('Your workspace access has been suspended. Contact its administrator.')
        ensure_seat(invitation.tenant, existing)
        _, role = workspace_roles(invitation.tenant)
        membership, _ = Membership.objects.get_or_create(
            tenant=invitation.tenant, user=request.user, defaults={'role': role},
        )
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted_at'])
        audit(invitation, request.user, 'accept')
        return Response(workspace_data(membership))


class RolesView(APIView):
    def get(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        from .models import Role
        return Response([{'id': role.pk, 'name': role.name, 'permissions': list(role.permissions.values_list('code', flat=True))} for role in Role.objects.filter(tenant=membership.tenant)])

    @transaction.atomic
    def post(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        from .models import Role, Permission
        name = serializers.CharField(max_length=80).run_validation(request.data.get('name'))
        codes = serializers.ListField(child=serializers.ChoiceField(choices=['projects.manage', 'finance.view', 'finance.manage']), max_length=3).run_validation(request.data.get('permissions', []))
        if Role.objects.filter(tenant=membership.tenant, name=name).exists():
            raise serializers.ValidationError('This role name already exists.')
        role = Role.objects.create(tenant=membership.tenant, name=name)
        for code in codes:
            permission, _ = Permission.objects.get_or_create(tenant=membership.tenant, code=code, defaults={'module': code.split('.')[0]})
            role.permissions.add(permission)
        audit(role, request.user, 'role.create', after={'name': name, 'permissions': codes})
        return Response({'id': role.pk, 'name': role.name, 'permissions': codes}, status=201)


class MemberAccessView(APIView):
    @transaction.atomic
    def patch(self, request, pk):
        from django.shortcuts import get_object_or_404
        from .models import Tenant, Role
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        Tenant.objects.select_for_update().get(pk=membership.tenant_id)
        member = get_object_or_404(Membership.objects.select_for_update(), pk=pk, tenant=membership.tenant)
        before = {'role': member.role_id, 'is_active': member.is_active}
        if 'role_id' in request.data:
            role_id = serializers.IntegerField(min_value=1).run_validation(request.data['role_id'])
            member.role = get_object_or_404(Role, pk=role_id, tenant=membership.tenant)
        if 'is_active' in request.data:
            active = serializers.BooleanField().run_validation(request.data['is_active'])
            if active and not member.is_active:
                from workspace_tools.quotas import ensure_seat
                ensure_seat(membership.tenant)
            member.is_active = active
        administrators = Membership.objects.filter(tenant=membership.tenant, is_active=True, user__is_active=True, role__permissions__code='workspace.manage').exclude(pk=member.pk).exists()
        if not administrators and not (member.is_active and member.role.permissions.filter(code='workspace.manage').exists()):
            raise serializers.ValidationError('Keep at least one active workspace administrator.')
        member.full_clean()
        member.save()
        audit(member, request.user, 'membership.update', before=before, after={'role': member.role_id, 'is_active': member.is_active})
        return Response({'id': member.pk, 'role_id': member.role_id, 'is_active': member.is_active})
