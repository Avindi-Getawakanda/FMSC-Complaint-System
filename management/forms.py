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