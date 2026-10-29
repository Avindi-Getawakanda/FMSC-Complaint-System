from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.models import UserProfile
from cases.models import Case, Category

from .models import Authority
from django.core.validators import FileExtensionValidator


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

    class ProgressUpdateForm(forms.Form):
        status = forms.ChoiceField(label="Case status")

    comment = forms.CharField(
        label="Progress details",
        strip=True,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Describe the work completed or next steps.",
            }
        ),
    )

    def __init__(self, *args, case, **kwargs):
        super().__init__(*args, **kwargs)

        allowed_statuses = {
            Case.Status.ASSIGNED: [
                Case.Status.NOT_STARTED,
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
            Case.Status.NOT_STARTED: [
                Case.Status.NOT_STARTED,
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
            Case.Status.IN_PROGRESS: [
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
            Case.Status.WAITING_INFO: [
                Case.Status.WAITING_INFO,
                Case.Status.IN_PROGRESS,
            ],
            Case.Status.REOPENED: [
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
        }

        available = allowed_statuses.get(case.status, [])
        labels = dict(Case.Status.choices)

        self.fields["status"].choices = [
            (status, labels[status])
            for status in available
        ]

        self.can_update = bool(available)

        if case.status in available:
            self.fields["status"].initial = case.status

    def clean(self):
        cleaned_data = super().clean()

        if not self.can_update:
            raise forms.ValidationError(
                "Progress cannot be updated in this case's current status."
            )

        return cleaned_data

class ProgressUpdateForm(forms.Form):
    status = forms.ChoiceField(label="Case status")

    comment = forms.CharField(
        label="Progress details",
        strip=True,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Describe the work completed or next steps.",
            }
        ),
    )

    evidence = forms.FileField(
        label="Supporting evidence",
        required=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "pdf"]
            )
        ],
        help_text="Optional. Upload a JPG, PNG or PDF, up to 5 MB.",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".jpg,.jpeg,.png,.pdf"}
        ),
    )

    def __init__(self, *args, case, **kwargs):
        super().__init__(*args, **kwargs)

        allowed_statuses = {
            Case.Status.ASSIGNED: [
                Case.Status.NOT_STARTED,
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
            Case.Status.NOT_STARTED: [
                Case.Status.NOT_STARTED,
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
            Case.Status.IN_PROGRESS: [
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
            Case.Status.WAITING_INFO: [
                Case.Status.WAITING_INFO,
                Case.Status.IN_PROGRESS,
            ],
            Case.Status.REOPENED: [
                Case.Status.IN_PROGRESS,
                Case.Status.WAITING_INFO,
            ],
        }

        available = allowed_statuses.get(case.status, [])
        labels = dict(Case.Status.choices)

        self.fields["status"].choices = [
            (status, labels[status])
            for status in available
        ]

        self.can_update = bool(available)

        if case.status in available:
            self.fields["status"].initial = case.status

    def clean_evidence(self):
        evidence = self.cleaned_data.get("evidence")

        if not evidence:
            return evidence

        if evidence.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "The file must be 5 MB or smaller."
            )

        return evidence

    def clean(self):
        cleaned_data = super().clean()

        if not self.can_update:
            raise forms.ValidationError(
                "Progress cannot be updated in this case's current status."
            )

        return cleaned_data