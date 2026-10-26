from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models

from cases.models import Case


class Authority(models.Model):
    name = models.CharField(max_length=150, unique=True)  # e.g. "IT Unit"
    unit = models.CharField(max_length=150, blank=True)
    officer_name = models.CharField(max_length=150, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authority",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "authorities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProgressUpdate(models.Model):
    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="progress_updates"
    )
    comment = models.TextField()
    status = models.CharField(max_length=20, choices=Case.Status.choices)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    evidence = models.FileField(upload_to="evidence/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.case.case_number} - {self.get_status_display()}"