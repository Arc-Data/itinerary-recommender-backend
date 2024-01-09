from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, email = None, password = None, **kwargs):
        UserModel = get_user_model()
        kwargs = {'email': email}

        try:
            user = UserModel.objects.get(**kwargs)
        except UserModel.DoesNotExist:
            raise Exception("No active account found with the given credentials")
        
        if not user.is_active:
            raise Exception("Account is inactive. Try checking your email for the activation link.")

        if user.check_password(password):
            print("correct password")
            return user
        else:
            raise Exception("Unable to log in with provided credentials")
        
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None