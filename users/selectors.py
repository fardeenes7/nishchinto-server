# users/selectors.py
from .models import User
from django.core.exceptions import ObjectDoesNotExist

def user_get_by_email(*, email: str) -> User:
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        raise ObjectDoesNotExist(f"User with email {email} does not exist.")
