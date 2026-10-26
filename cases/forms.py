
from pathlib import Path

from django import forms
from .models import Case, Category


class CaseSubmissionForm(forms.ModelForm):

    attachment = forms.FileField(
        required=False,
        label="Supporting Attachment",
        help_text="Optional: JPG, PNG, PDF or MP4 (maximum 10 MB).",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".jpg,.jpeg,.png,.pdf,.mp4"}
        ),
    )

    class Meta:
        model = Case
        fields = [
            "title",
            "description",
            "case_type",
            "priority",
            "category",
            "location",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Enter a short title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Describe your complaint or suggestion",
                }
            ),
            "location": forms.TextInput(
                attrs={"placeholder": "e.g. Lecture Hall, Library"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        )

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")

        if not attachment:
            return attachment

        allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf", ".mp4"}
        extension = Path(attachment.name).suffix.lower()

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                "Only JPG, PNG, PDF and MP4 files are allowed."
            )

        if attachment.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "The attachment must not exceed 10 MB."
            )

        return attachment
