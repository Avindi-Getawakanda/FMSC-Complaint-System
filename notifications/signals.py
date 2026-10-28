
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from cases.models import Case
from .models import Notification


@receiver(pre_save, sender=Case)
def capture_previous_case_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_notification_state = None
        return

    instance._previous_notification_state = (
        Case.objects.filter(pk=instance.pk)
        .values("status", "assigned_authority_id")
        .first()
    )


@receiver(post_save, sender=Case)
def create_case_change_notifications(sender, instance, created, **kwargs):
    if created:
        return

    previous = getattr(instance, "_previous_notification_state", None)

    if previous is None:
        return

    previous_status = previous["status"]
    previous_authority_id = previous["assigned_authority_id"]

    # Notify an authority when a case is assigned or reassigned.
    if (
        instance.assigned_authority_id
        and instance.assigned_authority_id != previous_authority_id
    ):
        authority = instance.assigned_authority

        if authority.user_id:
            Notification.objects.create(
                recipient=authority.user,
                case=instance,
                notification_type=Notification.Type.CASE_ASSIGNED,
                message=(
                    f"Case {instance.case_number} has been "
                    f"assigned to your authority."
                ),
            )

    # Notify the submitter when the case status changes.
    if instance.status != previous_status:
        if instance.status == Case.Status.REJECTED:
            notification_type = Notification.Type.CASE_REJECTED
            message = (
                f"Your case {instance.case_number} has been rejected."
            )
        elif instance.status in (
            Case.Status.SOLVED,
            Case.Status.CLOSED,
        ):
            notification_type = Notification.Type.CASE_RESOLVED
            message = (
                f"Your case {instance.case_number} is now "
                f"{instance.get_status_display().lower()}."
            )
        else:
            notification_type = Notification.Type.STATUS_UPDATED
            message = (
                f"The status of your case {instance.case_number} "
                f"has changed to {instance.get_status_display()}."
            )

        Notification.objects.create(
            recipient=instance.submitted_by,
            case=instance,
            notification_type=notification_type,
            message=message,
        )
