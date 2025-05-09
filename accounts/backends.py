from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check if the input matches username or email
            user = User.objects.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username)
            )
            
            # Verify password
            if user and user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # Run the default password hasher once to reduce timing
            # attacks detecting non-existent users
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Get the first matching user (should be rare with unique emails)
            user = User.objects.filter(
                Q(username__iexact=username) | 
                Q(email__iexact=username)
            ).first()
            
            if user and user.check_password(password):
                return user
                
        return None
