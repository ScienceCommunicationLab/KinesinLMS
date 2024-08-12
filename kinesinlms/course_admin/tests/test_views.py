from django.test import TestCase
from django.urls import reverse

from kinesinlms.assessments.tests.factories import (
    LongFormAssessmentFactory,
    SubmittedAnswerFactory,
)
from kinesinlms.course.models import CourseStaff, CourseUnit
from kinesinlms.course.tests.factories import (
    BlockFactory,
    CourseFactory,
    EnrollmentFactory,
)
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import UnitBlock
from kinesinlms.users.tests.factories import EducatorFactory, UserFactory
from kinesinlms.users.utils import create_default_groups


class TestCourseAdminAssessmentMixin:
    """
    Sets up data shared by the Course Admin "Assessment" view tests.
    """

    def setUp(self):
        super().setUp() # noqa
        create_default_groups()

        self.student1 = UserFactory()
        self.student2 = UserFactory()
        self.student3 = UserFactory()
        self.course = CourseFactory()

        # Let's assume this user is a "Course Staff" member but not a
        # Django 'staff' users. That way we make sure our CourseStaff model
        # and related permissions are working.
        self.course_staff = EducatorFactory.create(is_staff=False)
        CourseStaff.objects.create(course=self.course, user=self.course_staff)
        # sanity check
        assert self.course_staff.is_educator is True

        EnrollmentFactory(student=self.student1, course=self.course)
        EnrollmentFactory(student=self.student2, course=self.course)
        EnrollmentFactory(student=self.student3, course=self.course)

        self.block1 = BlockFactory(type=BlockType.ASSESSMENT.name)
        self.block2 = BlockFactory(type=BlockType.ASSESSMENT.name)
        self.assessment1 = LongFormAssessmentFactory(block=self.block1)
        self.assessment2 = LongFormAssessmentFactory(block=self.block2)
        course_unit = CourseUnit.objects.create(course=self.course)
        UnitBlock.objects.create(block=self.block1, course_unit=course_unit)
        UnitBlock.objects.create(block=self.block2, course_unit=course_unit)
        course_unit.save()

        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment1,
            student=self.student1,
        )
        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment2,
            student=self.student1,
        )
        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment2,
            student=self.student2,
        )

        self.assessment_index = reverse(
            "course:course_admin:assessments",
            kwargs={
                "course_run": self.course.run,
                "course_slug": self.course.slug,
            },
        )
        self.delete_submitted_answers_url = reverse(
            "course:course_admin:delete_submitted_answers",
            kwargs={
                "course_run": self.course.run,
                "course_slug": self.course.slug,
            },
        )
        self.rescore_assessments_url = reverse(
            "course:course_admin:rescore_submitted_answers",
            kwargs={
                "course_run": self.course.run,
                "course_slug": self.course.slug,
            },
        )


class TestCourseAdminAssessmentsView(TestCourseAdminAssessmentMixin, TestCase):
    def test_assessments_index(self):
        self.client.force_login(self.course_staff)
        url = reverse(
            "course:course_admin:assessments",
            kwargs={
                "course_run": self.course.run,
                "course_slug": self.course.slug,
            },
        )
        response = self.client.get(url)
        self.assertContains(response, text="Delete Submitted Answers")
        self.assertContains(response, text="Re-score Assessments")


class TestCourseAdminDeleteAnswersView(TestCourseAdminAssessmentMixin, TestCase):
    """
    Test the "Delete Submitted Answers" Course Admin view.
    """

    def setUp(self):
        super().setUp()

        self.delete_submitted_answers_url = reverse(
            "course:course_admin:delete_submitted_answers",
            kwargs={
                "course_run": self.course.run,
                "course_slug": self.course.slug,
            },
        )

    def test_get_delete_submitted_answers(self):
        self.client.force_login(self.course_staff)
        response = self.client.get(self.delete_submitted_answers_url)

        self.assertContains(response, text="Delete Submitted Answers")
        self.assertContains(response, text="Student")
        self.assertContains(response, text="Assessment")

    def test_delete_submitted_answers_for_course(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(self.delete_submitted_answers_url)

        self.assertContains(
            response,
            text=(
                "Deleted 3 answers submitted\n          "
                "to all assessments\n          "
                "by all students."
            ),
        )

    def test_delete_submitted_answers_for_student(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.delete_submitted_answers_url, data={"student": self.student1.id}
        )
        self.assertContains(
            response,
            text=(
                "Deleted 2 answers submitted\n          "
                "to all assessments\n          "
                f'by "{self.student1}".'
            ),
        )

    def test_delete_submitted_answers_for_assessment(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.delete_submitted_answers_url, data={"assessment": self.assessment2.id}
        )
        self.assertContains(
            response,
            text=(
                "Deleted 2 answers submitted\n          "
                f'to "{self.assessment2}"\n          '
                "by all students."
            ),
        )

    def test_delete_submitted_answers_for_assessment_student(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.delete_submitted_answers_url,
            data={"assessment": self.assessment2.id, "student": self.student2.id},
        )
        self.assertContains(
            response,
            text=(
                "Deleted 1 answers submitted\n          "
                f'to "{self.assessment2}"\n          '
                f'by "{self.student2}".'
            ),
        )

    def test_delete_submitted_answers_no_submissions(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.delete_submitted_answers_url, data={"student": self.student3.id}
        )
        self.assertContains(
            response,
            text=(
                "Deleted 0 answers submitted\n          "
                "to all assessments\n          "
                f'by "{self.student3}".'
            ),
        )

    def test_delete_submitted_answers_staff_only(self):
        self.client.force_login(self.student1)
        response = self.client.post(self.delete_submitted_answers_url)
        assert response.status_code == 403

    def test_delete_submitted_answers_bad_course(self):
        self.client.force_login(self.course_staff)
        bad_course_url = reverse(
            "course:course_admin:delete_submitted_answers",
            kwargs={
                "course_run": "invalid_run",
                "course_slug": "invalid_slug",
            },
        )
        response = self.client.post(bad_course_url)
        # It's a 403 not 404 because the course_staff_required decorator will
        # be the first to fail.
        assert response.status_code == 403

    def test_delete_submitted_answers_student_not_enrolled(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.delete_submitted_answers_url, data={"student": self.course_staff.id}
        )
        self.assertContains(
            response,
            text=(
                "Select a valid choice. That choice is not one of the available choices."
            ),
        )

    def test_delete_submitted_answers_bad_assessment(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.delete_submitted_answers_url, data={"assessment": 123456}
        )
        self.assertContains(
            response,
            text=(
                "Select a valid choice. That choice is not one of the available choices."
            ),
        )


class TestCourseAdminRescoreView(TestCourseAdminAssessmentMixin, TestCase):
    """
    Test the "Re-score Assessments" Course Admin view.
    """

    def setUp(self):
        super().setUp()

        self.rescore_assessments_url = reverse(
            "course:course_admin:rescore_submitted_answers",
            kwargs={
                "course_run": self.course.run,
                "course_slug": self.course.slug,
            },
        )

    def test_get_rescore_assessment_progress(self):
        self.client.force_login(self.course_staff)
        response = self.client.get(self.rescore_assessments_url)
        self.assertContains(response, text="Re-score Assessments")
        self.assertContains(response, text="Student")

    def test_rescore_assessment_progress_for_course(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(self.rescore_assessments_url)
        self.assertContains(
            response,
            text=(
                "Re-scoring 3 answers submitted\n          "
                "to all assessments\n          "
                "by all students."
            ),
        )

    def test_rescore_assessment_progress_for_student(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.rescore_assessments_url, data={"student": self.student1.id}
        )
        self.assertContains(
            response,
            text=(
                "Re-scoring 2 answers submitted\n          "
                "to all assessments\n          "
                f'by "{self.student1}".'
            ),
        )

    def test_rescore_submitted_answers_for_assessment(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.rescore_assessments_url, data={"assessment": self.assessment2.id}
        )
        self.assertContains(
            response,
            text=(
                "Re-scoring 2 answers submitted\n          "
                f'to "{self.assessment2}"\n          '
                "by all students."
            ),
        )

    def test_rescore_submitted_answers_for_assessment_student(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.rescore_assessments_url,
            data={"assessment": self.assessment2.id, "student": self.student2.id},
        )
        self.assertContains(
            response,
            text=(
                "Re-scoring 1 answers submitted\n          "
                f'to "{self.assessment2}"\n          '
                f'by "{self.student2}".'
            ),
        )

    def test_rescore_assessment_progress_no_submissions(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.rescore_assessments_url, data={"student": self.student3.id}
        )
        self.assertContains(
            response,
            text=(
                "Re-scoring 0 answers submitted\n          "
                "to all assessments\n          "
                f'by "{self.student3}".'
            ),
        )

    def test_rescore_assessment_progress_staff_only(self):
        self.client.force_login(self.student1)
        response = self.client.post(self.rescore_assessments_url)
        assert response.status_code == 403

    def test_rescore_assessment_progress_bad_course(self):
        self.client.force_login(self.course_staff)
        bad_course_url = reverse(
            "course:course_admin:rescore_submitted_answers",
            kwargs={
                "course_run": "invalid_run",
                "course_slug": "invalid_slug",
            },
        )
        response = self.client.post(bad_course_url)
        # It's a 403 not 404 because the course_staff_required decorator is first to fail.
        assert response.status_code == 403

    def test_rescore_assessment_progress_student_not_enrolled(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.rescore_assessments_url, data={"student": self.course_staff.id}
        )
        self.assertContains(
            response,
            text=(
                "Select a valid choice. That choice is not one of the available choices."
            ),
        )

    def test_rescore_submitted_answers_bad_assessment(self):
        self.client.force_login(self.course_staff)
        response = self.client.post(
            self.rescore_assessments_url, data={"assessment": 123456}
        )
        self.assertContains(
            response,
            text=(
                "Select a valid choice. That choice is not one of the available choices."
            ),
        )
