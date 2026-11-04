from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import UserProfile


class MatriculeBackend(ModelBackend):
    """Authentification par matricule (champ matricule de UserProfile) au lieu du username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            profile = UserProfile.objects.select_related("user").get(matricule=username)
        except UserProfile.DoesNotExist:
            return None
        user = profile.user
        if user.is_staff:
            return None  # Laisser ModelBackend gérer (confirm_login_allowed lèvera l'erreur staff)
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None