import uuid

from django.conf import settings
from django.db import models


def generate_case_number():
    return f"FMSC-{uuid.uuid4().hex[:12].upper()}"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Case(models.Model):

    class CaseType(models.TextChoices):
        COMPLAINT = "complaint", "Complaint"
        SUGGESTION = "suggestion", "Suggestion"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        NOT_STARTED = "not_started", "Not Started"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING_INFO = "waiting_info", "Waiting for Information"
        SOLVED = "solved", "Solved"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"
        REOPENED = "reopened", "Reopened"

    case_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_case_number,
        editable=False,
    )
    title = models.CharField(max_length=200)
    description = models.TextField()

    case_type = models.CharField(
        max_length=20,
        choices=CaseType.choices,
        default=CaseType.COMPLAINT,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="cases",
    )
    location = models.CharField(max_length=200)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_cases",
    )
    assigned_authority = models.ForeignKey(
        "management.Authority",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_cases",
    )

    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    solved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case_number} - {self.title}"


class Attachment(models.Model):
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="cases/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.case.case_number}"


class AuditLog(models.Model):
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    action = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.case.case_number} - {self.action}"