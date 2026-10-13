from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.db import transaction
from rest_framework import serializers, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from workspace_tools.services import enqueue

User = get_user_model()


def send_verification(user):
    token = signing.dumps({'user': user.pk, 'email': user.email}, salt='email-verification')
    link = f'{settings.FRONTEND_URL.rstrip("/")}/account/verify?{urlencode({"token": token})}'
    enqueue('email', {'to': user.email, 'subject': 'Verify your TeamFlow email', 'body': f'Confirm your email address within 24 hours:\n{link}'})


class AuthRateLimit:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class LoginView(AuthRateLimit, TokenObtainPairView):
    pass


class RefreshView(AuthRateLimit, TokenRefreshView):
    pass


class ResetRequestView(AuthRateLimit, APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        email = serializers.EmailField().run_validation(request.data.get('email'))
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user and user.has_usable_password():
            query = urlencode({'uid': urlsafe_base64_encode(force_bytes(user.pk)), 'token': default_token_generator.make_token(user)})
            link = f'{settings.FRONTEND_URL.rstrip("/")}/account/reset?{query}'
            enqueue('email', {'to': user.email, 'subject': 'Reset your TeamFlow password', 'body': f'Reset your password using this link:\n{link}\nIf you did not request this, ignore this message.'})
        return Response({'detail': 'If this account exists, a password reset email has been queued.'})


class ResetConfirmView(AuthRateLimit, APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        uid = serializers.CharField(max_length=100).run_validation(request.data.get('uid'))
        token = serializers.CharField(max_length=200).run_validation(request.data.get('token'))
        password = serializers.CharField(max_length=128, trim_whitespace=False).run_validation(request.data.get('password'))
        try:
            user = User.objects.select_for_update().get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, UnicodeDecodeError, OverflowError):
            raise serializers.ValidationError('Invalid or expired reset link.')
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError('Invalid or expired reset link.')
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        user.set_password(password)
        user.save(update_fields=['password'])
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        return Response({'detail': 'Password reset. Sign in with your new password.'})


class VerificationRequestView(AuthRateLimit, APIView):
    def post(self, request):
        if not request.user.email_verified:
            send_verification(request.user)
        return Response({'detail': 'Verification email queued.'})


class VerificationConfirmView(AuthRateLimit, APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        token = serializers.CharField(max_length=1000).run_validation(request.data.get('token'))
        try:
            data = signing.loads(token, salt='email-verification', max_age=86400)
            user = User.objects.get(pk=data['user'], email=data['email'], is_active=True)
        except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError):
            raise serializers.ValidationError('Invalid or expired verification link.')
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        return Response({'detail': 'Email verified.'})


class LogoutView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh', ''))
            if str(token['user_id']) != str(request.user.pk):
                raise TokenError('Invalid token owner.')
            token.blacklist()
        except (TokenError, KeyError, TypeError):
            raise serializers.ValidationError('Invalid refresh token.')
        return Response(status=204)
