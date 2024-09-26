from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from accounts.models import User
from accounts.forms import SignupForm, LoginForm

# Create your views here.


# CBV 기반
signup = CreateView.as_view(
    model=User,
    form_class=SignupForm,
    template_name="accounts/signup_form.html",
    success_url=reverse_lazy("accounts:login"),
)

login = LoginView.as_view(
    form_class=LoginForm, template_name="accounts/login_form.html"
)


logout = LogoutView.as_view(next_page="accounts:login")


@login_required
def profile(request):
    return render(request, "accounts/profile.html", {"user": request.user})
