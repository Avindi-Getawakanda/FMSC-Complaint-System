
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile


class CustomRegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (UserProfile.Role.STUDENT, "Student"),
            (UserProfile.Role.LECTURER, "Lecturer"),
        ],
        label="Account Type",
        widget=forms.Select()
    )

    department = forms.CharField(
        max_length=150,
        label="Department",
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your department"
        })
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "role", "department")
