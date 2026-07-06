from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SignupSerializer, UserSerializer


class SignupView(generics.CreateAPIView):
    """POST email/password/first_name/last_name -> creates an account.

    Open to anyone (no auth required to sign up). Log in afterwards via
    /api/auth/token/ to get a JWT access/refresh pair.
    """
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    """GET the currently authenticated user -- handy for the React app to
    check "am I logged in, and who am I" right after loading a stored token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)