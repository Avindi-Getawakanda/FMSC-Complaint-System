from django.db import models
from django.conf import settings
# Create your models here.


class UserProfile(models.Model):

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        LECTURER = "lecturer", "Lecturer"
        ADMINISTRATOR = "administrator", "Administrator"
        AUTHORITY = "authority", "Authority"
        MANAGEMENT = "management", "Management Viewer"
        SYSTEM_ADMIN = "system_admin", "System Administrator"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )

    department = models.CharField(
        max_length=150,
        blank=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

