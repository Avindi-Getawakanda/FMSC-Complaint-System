
from django.conf import settings
from django.db import models


class Notification(models.Model):

    class Type(models.TextChoices):
        CASE_SUBMITTED = "case_submitted", "Case Submitted"
        CASE_ASSIGNED = "case_assigned", "Case Assigned"
        STATUS_UPDATED = "status_updated", "Status Updated"
        CASE_RESOLVED = "case_resolved", "Case Resolved"
        CASE_REJECTED = "case_rejected", "Case Rejected"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )

    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.get_notification_type_display()}"
