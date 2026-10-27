from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.models import UserProfile
from cases.models import Case, Category

from .models import Authority


class CaseAssignmentForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ["category", "priority", "assigned_authority"]

        labels = {
            "assigned_authority": "Assign to",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        )

        self.fields["assigned_authority"].queryset = Authority.objects.filter(
            is_active=True
        )

        self.fields["assigned_authority"].required = True
        self.fields["assigned_authority"].empty_label = "Select an authority"


class CaseRejectionForm(forms.ModelForm):
    rejection_reason = forms.CharField(
        label="Reason for rejection",
        required=True,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Explain why this case is being rejected.",
            }
        ),
        error_messages={
            "required": "Please provide a reason for rejecting this case.",
        },
    )

    class Meta:
        model = Case
        fields = ["rejection_reason"]


class AuthorityForm(forms.ModelForm):
    class Meta:
        model = Authority
        fields = [
            "name",
            "unit",
            "officer_name",
            "designation",
            "email",
            "phone",
            "user",
            "is_active",
        ]

        labels = {
            "name": "Authority name",
            "unit": "Department / unit",
            "officer_name": "Responsible officer",
            "user": "Linked authority account",
            "is_active": "Active authority",
        }

        help_texts = {
            "user": (
                "Optional. Select an existing active user with the "
                "Authority role. Each account can belong to one authority."
            ),
            "is_active": (
                "Active authorities are available for case assignment."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()

        available_users = User.objects.filter(
            is_active=True,
            profile__role=UserProfile.Role.AUTHORITY,
        )

        if self.instance.pk:
            available_users = available_users.filter(
                Q(authority__isnull=True)
                | Q(authority=self.instance)
            )
        else:
            available_users = available_users.filter(
                authority__isnull=True
            )

        self.fields["user"].queryset = available_users.order_by(
            User.USERNAME_FIELD
        )
        self.fields["user"].empty_label = "No account linked"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        existing = Authority.objects.filter(name__iexact=name)

        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError(
                "An authority with this name already exists."
            )

        return name