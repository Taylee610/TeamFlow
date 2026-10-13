from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SignupSerializer, UserSerializer
from rest_framework.throttling import ScopedRateThrottle


class SignupView(generics.CreateAPIView):
    """POST email/password/first_name/last_name -> creates an account.

    Open to anyone (no auth required to sign up). Log in afterwards via
    /api/auth/token/ to get a JWT access/refresh pair.
    """
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def perform_create(self, serializer):
        from django.db import transaction
        from .recovery import send_verification
        with transaction.atomic():
            user = serializer.save()
            send_verification(user)


class MeView(APIView):
    """GET the currently authenticated user -- handy for the React app to
    check "am I logged in, and who am I" right after loading a stored token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
