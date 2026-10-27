
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from cases.models import Case, Category


class MyCasesSecurityTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.student_a = User.objects.create_user(
            username="test_student_a",
            password="TestPass123!",
        )

        self.student_b = User.objects.create_user(
            username="test_student_b",
            password="TestPass123!",
        )

        # Ensure both test accounts have student roles.
        for user in (self.student_a, self.student_b):
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": UserProfile.Role.STUDENT},
            )

        self.category = Category.objects.create(
            name="Test Category"
        )

        self.case = Case.objects.create(
            title="Test Complaint",
            description="A complaint for security testing.",
            case_type=Case.CaseType.COMPLAINT,
            category=self.category,
            location="Faculty",
            submitted_by=self.student_a,
        )

    def test_owner_can_view_case(self):
        self.client.force_login(self.student_a)

        response = self.client.get(
            reverse("case_detail", args=[self.case.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_other_student_cannot_view_case(self):
        self.client.force_login(self.student_b)

        response = self.client.get(
            reverse("case_detail", args=[self.case.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_other_student_cannot_see_case_in_list(self):
        self.client.force_login(self.student_b)

        response = self.client.get(reverse("my_cases"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.case.case_number)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(
            reverse("case_detail", args=[self.case.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

