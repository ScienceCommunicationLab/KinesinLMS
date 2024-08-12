import logging
from typing import Optional
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.models import CohortMembership, CohortType, Enrollment, Course
from kinesinlms.course.tests.factories import CourseFactory, CohortFactory
from kinesinlms.email_automation.tests.factories import EmailAutomationProviderFactory
from kinesinlms.email_automation.utils import get_email_automation_provider
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)

User = get_user_model()


class TestBatchUnenroll(TestCase):
    """
    Test that the batch unenrollment does indeed unenroll
    the set of students provided to it.

    Also, make sure that it notifies an ostensibly configured
    email automation system by calling the EmailAutomationNotifier.

    """

    course: Optional[Course] = None
    student_1: Optional[User] = None
    student_2: Optional[User] = None
    default_cohort: Optional[User] = None

    @classmethod
    def setUpTestData(cls):
        cls.course = CourseFactory()
        cls.admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)

        cls.student_1 = UserFactory(username="student_1",
                                    email="student_1@example.com")
        cls.student_2 = UserFactory(username="student_2",
                                    email="student_2@example.com")

        cls.default_cohort = CohortFactory(course=cls.course,
                                           type=CohortType.DEFAULT.name,
                                           slug=CohortType.DEFAULT.name)

        Enrollment.objects.get_or_create(student=cls.student_1,
                                         course=cls.course,
                                         active=True)
        Enrollment.objects.get_or_create(student=cls.student_2,
                                         course=cls.course,
                                         active=True)

        cls.default_cohort.students.set([cls.student_1, cls.student_2])

        cls.unenroll_url = reverse('management:students_manual_unenrollment')

    def test_rando_cannot_call(self):
        self.client.logout()
        # Not logged in user.
        data = {
            "course": self.course.id,
            "students": f"{self.student_1.email}\n{self.student_2.email}"
        }
        response = self.client.post(self.unenroll_url, data=data)
        # Should redirect to log in
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_call(self):
        self.client.logout()
        self.client.force_login(self.student_1)
        data = {
            "course": self.course.id,
            "students": f"{self.student_1.email}\n{self.student_2.email}"
        }
        response = self.client.post(self.unenroll_url, data=data)
        self.assertEqual(response.status_code, 403)

    def test_batch_unenroll(self):
        self.client.logout()
        self.client.force_login(self.admin_user)

        # Make sure both students enrolled
        enrollment_1 = Enrollment.objects.get(student=self.student_1, course=self.course)
        self.assertEqual(True, enrollment_1.active)
        enrollment_2 = Enrollment.objects.get(student=self.student_2, course=self.course)
        self.assertEqual(True, enrollment_2.active)

        # Make sure in cohorts
        membership_1_exists = CohortMembership.objects.filter(student=self.student_1,
                                                              cohort=self.default_cohort).exists()
        self.assertTrue(membership_1_exists)
        membership_2_exists = CohortMembership.objects.filter(student=self.student_2,
                                                              cohort=self.default_cohort).exists()
        self.assertTrue(membership_2_exists)

        # Run batch unenroll
        self.client.force_login(self.admin_user)
        data = {
            "course": self.course.id,
            "students": f"{self.student_1.email}\n{self.student_2.email}"
        }
        self.client.post(self.unenroll_url, data=data)

        # Make sure both students unenrolled
        enrollment_1 = Enrollment.objects.get(student=self.student_1, course=self.course)
        self.assertEqual(False, enrollment_1.active)
        enrollment_2 = Enrollment.objects.get(student=self.student_2, course=self.course)
        self.assertEqual(False, enrollment_2.active)

        # Make sure not in cohorts anymore
        membership_1_exists = CohortMembership.objects.filter(student=self.student_1,
                                                              cohort=self.default_cohort).exists()
        self.assertFalse(membership_1_exists)
        membership_2_exists = CohortMembership.objects.filter(student=self.student_1,
                                                              cohort=self.default_cohort).exists()
        self.assertFalse(membership_2_exists)

        logger.debug("Done.")

    @patch('kinesinlms.tracking.tracker.EmailAutomationNotifier')
    def test_batch_unenroll_notifies_email_automation_provider(self, mock_email_automation_notifier: MagicMock):
        """
        When students are batch unenrolled by an admin, we still want
        any email automations to be notified of the unenroll event for each student.
        """
        self.client.logout()
        self.client.force_login(self.admin_user)

        site = Site.objects.get_current()
        EmailAutomationProviderFactory.create(site=site)

        # Sanity check
        email_automation_provider = get_email_automation_provider()
        self.assertIsNotNone(email_automation_provider)

        mock_email_automation_notifier.handle_tracker_event.return_value = True

        # Make sure both students enrolled
        enrollment_1 = Enrollment.objects.get(student=self.student_1, course=self.course)
        self.assertEqual(True, enrollment_1.active)
        enrollment_2 = Enrollment.objects.get(student=self.student_2, course=self.course)
        self.assertEqual(True, enrollment_2.active)

        # Make sure in cohorts
        membership_1_exists = CohortMembership.objects.filter(student=self.student_1,
                                                              cohort=self.default_cohort).exists()
        self.assertTrue(membership_1_exists)
        membership_2_exists = CohortMembership.objects.filter(student=self.student_2,
                                                              cohort=self.default_cohort).exists()
        self.assertTrue(membership_2_exists)

        # Run batch unenroll
        self.client.force_login(self.admin_user)
        data = {
            "course": self.course.id,
            "students": f"{self.student_1.email}\n{self.student_2.email}"
        }
        self.client.post(self.unenroll_url, data=data)

        # Make sure both students unenrolled
        enrollment_1 = Enrollment.objects.get(student=self.student_1, course=self.course)
        self.assertEqual(False, enrollment_1.active)
        enrollment_2 = Enrollment.objects.get(student=self.student_2, course=self.course)
        self.assertEqual(False, enrollment_2.active)

        # Make sure not in cohorts anymore
        membership_1_exists = CohortMembership.objects.filter(student=self.student_1,
                                                              cohort=self.default_cohort).exists()
        self.assertFalse(membership_1_exists)
        membership_2_exists = CohortMembership.objects.filter(student=self.student_1,
                                                              cohort=self.default_cohort).exists()
        self.assertFalse(membership_2_exists)

        # Make sure unenroll called email notifier, if configured.
        if settings.EMAIL_AUTOMATION_PROVIDER_API_KEY:
            mock_email_automation_notifier.handle_tracker_event.assert_called()
            self.assertEqual(mock_email_automation_notifier.handle_tracker_event.call_count, 2)

        logger.debug("Done.")
