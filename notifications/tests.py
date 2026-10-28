
from django.contrib.auth import get_user_model
from django.test import TestCase

from cases.models import Case, Category
from management.models import Authority
from .models import Notification

from django.urls import reverse


class NotificationSignalTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.student = User.objects.create_user(
            username="notification_student",
            password="TestPassword123!",
        )

        self.authority_user = User.objects.create_user(
            username="notification_authority",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Notification Test Category",
        )

        self.authority = Authority.objects.create(
            name="Notification Test Authority",
            user=self.authority_user,
        )

        self.case = Case.objects.create(
            title="Test Wi-Fi Complaint",
            description="Wi-Fi is not working.",
            case_type=Case.CaseType.COMPLAINT,
            priority=Case.Priority.NORMAL,
            category=self.category,
            location="Computer Lab",
            submitted_by=self.student,
        )

    def test_authority_receives_assignment_notification(self):
        self.case.assigned_authority = self.authority
        self.case.status = Case.Status.ASSIGNED
        self.case.save()

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.authority_user,
                case=self.case,
                notification_type=Notification.Type.CASE_ASSIGNED,
            ).exists()
        )

    def test_submitter_receives_rejection_notification(self):
        self.case.status = Case.Status.REJECTED
        self.case.save()

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                case=self.case,
                notification_type=Notification.Type.CASE_REJECTED,
            ).exists()
        )

    def test_submitter_receives_resolution_notification(self):
        self.case.status = Case.Status.SOLVED
        self.case.save()

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                case=self.case,
                notification_type=Notification.Type.CASE_RESOLVED,
            ).exists()
        )

    def test_no_duplicate_notification_on_unchanged_save(self):
        self.case.status = Case.Status.UNDER_REVIEW
        self.case.save()

        initial_count = Notification.objects.filter(
            case=self.case
        ).count()

        self.case.save()

        self.assertEqual(
            Notification.objects.filter(case=self.case).count(),
            initial_count,
        )

    def test_no_assignment_notification_without_linked_user(self):
        unlinked_authority = Authority.objects.create(
            name="Unlinked Test Authority",
        )

        self.case.assigned_authority = unlinked_authority
        self.case.status = Case.Status.ASSIGNED
        self.case.save()

        self.assertFalse(
            Notification.objects.filter(
                case=self.case,
                notification_type=Notification.Type.CASE_ASSIGNED,
            ).exists()
        )


class NotificationSecurityTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.student = User.objects.create_user(
            username="security_student",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="security_other",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Security Test Category",
        )

        self.case = Case.objects.create(
            title="Security Test Case",
            description="Testing notification permissions.",
            case_type=Case.CaseType.COMPLAINT,
            priority=Case.Priority.NORMAL,
            category=self.category,
            location="FMSC",
            submitted_by=self.student,
        )

        self.notification = Notification.objects.create(
            recipient=self.student,
            case=self.case,
            notification_type=Notification.Type.CASE_SUBMITTED,
            message="Test notification",
        )

    def test_notification_page_requires_login(self):
        response = self.client.get(
            reverse("notifications:list")
        )

        self.assertEqual(response.status_code, 302)

    def test_user_only_sees_own_notifications(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse("notifications:list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            "Test notification",
        )

    def test_user_cannot_mark_others_notification_as_read(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "notifications:mark_read",
                args=[self.notification.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_mark_as_read_requires_post(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "notifications:mark_read",
                args=[self.notification.pk],
            )
        )

        self.assertEqual(response.status_code, 405)

        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_mark_all_as_read_only_updates_own_notifications(self):
        other_notification = Notification.objects.create(
            recipient=self.other_user,
            case=self.case,
            notification_type=Notification.Type.STATUS_UPDATED,
            message="Other user's notification",
        )

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("notifications:mark_all_read")
        )

        self.assertEqual(response.status_code, 302)

        self.notification.refresh_from_db()
        other_notification.refresh_from_db()

        self.assertTrue(self.notification.is_read)
        self.assertFalse(other_notification.is_read)