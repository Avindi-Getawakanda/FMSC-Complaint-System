from django import forms

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