from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
)  # user 모델에 대한 모델폼을 지원해줌

from accounts.models import User


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = User
        fields = ["username"]


class LoginForm(AuthenticationForm):
    pass
