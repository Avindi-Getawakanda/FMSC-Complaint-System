# Create your views here.
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import render, redirect

from .models import UserProfile


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()

        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.STUDENT
        )

        login(request, user)
        messages.success(request, "Your account has been created successfully!")
        return redirect("dashboard")

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Logged in successfully!")
        return redirect("dashboard")

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect("login")

    return redirect("dashboard")


@login_required
def dashboard_view(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"role": UserProfile.Role.STUDENT}
    )

    return render(request, "accounts/dashboard.html", {
        "profile": profile
    })


