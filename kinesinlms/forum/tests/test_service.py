"""
Test the Forum Service.

In many of the tests below we're mocking the DiscourseClient, so an actual Discourse
instance is not required to be running

"""
import logging
from unittest.mock import patch, MagicMock

from django.contrib.sites.models import Site
from django.test import TestCase

from kinesinlms.course.models import CohortType
from kinesinlms.course.tests.factories import CourseFactory, CohortFactory
from kinesinlms.forum.models import ForumSubcategoryType
from kinesinlms.forum.tests.factories import ForumCategoryFactory, CourseForumGroupFactory, \
    FormCohortGroupFactory, ForumProviderFactory
from kinesinlms.forum.utils import get_forum_service
from kinesinlms.users.tests.factories import UserFactory

logger = logging.getLogger(__name__)


class TestForumService(TestCase):

    def setUp(self):
        self.course = CourseFactory()
        self.student_1 = UserFactory(username="default_cohort_student",
                                     email="default_cohort_student@example.com")
        self.student_2 = UserFactory(username="special_cohort_student",
                                     email="special_cohort_student@example.com")
        self.default_cohort = CohortFactory(course=self.course,
                                            type=CohortType.DEFAULT.name,
                                            slug=CohortType.DEFAULT.name)
        self.default_cohort.students.set([self.student_1])
        self.special_cohort = CohortFactory(course=self.course,
                                            type=CohortType.CUSTOM.name,
                                            slug="special")
        self.special_cohort.students.set([self.student_2])

        site = Site.objects.get_current()
        self.forum_provider = ForumProviderFactory.create(site=site)

        self.student_1 = self.student_1
        self.student_2 = self.student_1
        self.default_cohort = self.default_cohort
        self.special_cohort = self.special_cohort

    def test_get_or_create_forum_group(self):
        discourse_client_mock = MagicMock()
        discourse_client_mock.create_group.return_value = {
            "basic_group": {
                "id": 12
            }
        }

        with patch('kinesinlms.forum.service.discourse_service.DiscourseClient', return_value=discourse_client_mock):
            service = get_forum_service()
            course_forum_group, created = service.get_or_create_course_forum_group(self.course)
            self.assertEqual(course_forum_group.course, self.course)
            self.assertEqual(course_forum_group.name, self.course.token)
            self.assertEqual(course_forum_group.group_id, 12)

    def test_get_or_create_cohort_forum_group(self):
        discourse_client_mock = MagicMock()
        discourse_client_mock.create_group.return_value = {
            "basic_group": {
                "id": 13
            }
        }

        with patch('kinesinlms.forum.service.discourse_service.DiscourseClient', return_value=discourse_client_mock):
            service = get_forum_service()
            default_cohort = self.course.get_default_cohort()
            cohort_forum_group, created = service.get_or_create_cohort_forum_group(cohort=default_cohort)
            self.assertEqual(cohort_forum_group.group_id, 13)

    def test_create_forum_category_for_course(self):
        """
        Test creating a forum category for a course
        """

        discourse_client_mock = MagicMock()
        discourse_client_mock.site.return_value = {
            "categories": []
        }
        discourse_client_mock.create_category.return_value = {
            "category": {
                "id": 13,
                "slug": "test-2020"
            }
        }

        # Assume a CourseForumGroup already exists
        CourseForumGroupFactory(course=self.course, group_id=20)

        with patch('kinesinlms.forum.service.discourse_service.DiscourseClient', return_value=discourse_client_mock):
            service = get_forum_service()
            forum_category, created = service.get_or_create_forum_category(course=self.course)
            self.assertEqual(forum_category.course, self.course)
            self.assertEqual(forum_category.category_id, 13)
            self.assertEqual(forum_category.category_slug, "test-2020")

    def test_create_subcategory_for_all_enrolled(self):
        discourse_client_mock = MagicMock()

        discourse_client_mock.create_category.return_value = {
            "category": {
                "id": 13
            }
        }

        parent_category = ForumCategoryFactory(
            course=self.course,
            category_id=1,
            category_slug="test-2020"
        )

        course_forum_group = CourseForumGroupFactory(
            course=self.course,
            group_id=20,
        )

        with patch('kinesinlms.forum.service.discourse_service.DiscourseClient', return_value=discourse_client_mock):
            service = get_forum_service()
            forum_subcategory, created = service.get_or_create_forum_subcategory(
                forum_category=parent_category,
                subcategory_type=ForumSubcategoryType.ALL_ENROLLED.name
            )
            self.assertTrue(created)
            self.assertEqual(forum_subcategory.forum_category, parent_category)
            self.assertEqual(forum_subcategory.type, ForumSubcategoryType.ALL_ENROLLED.name)
            self.assertEqual(forum_subcategory.course_forum_group, course_forum_group)
            self.assertEqual(forum_subcategory.cohort_forum_group, None)
            self.assertEqual(forum_subcategory.subcategory_id, 13)

    def test_create_subcategory_for_cohort(self):
        discourse_client_mock = MagicMock()

        discourse_client_mock.create_category.return_value = {
            "category": {
                "id": 14
            }
        }

        parent_category = ForumCategoryFactory(
            course=self.course,
            category_id=1,
            category_slug="test-2020"
        )

        with patch('kinesinlms.forum.service.discourse_service.DiscourseClient', return_value=discourse_client_mock):
            cohort_forum_group = FormCohortGroupFactory(
                group_id=20,
                name="test-2020-co-DEFAULT"
            )
            self.special_cohort.forum_group = cohort_forum_group
            self.special_cohort.save()

            service = get_forum_service()
            forum_subcategory, created = service.get_or_create_forum_subcategory(
                forum_category=parent_category,
                subcategory_type=ForumSubcategoryType.COHORT.name,
                cohort_forum_group=cohort_forum_group
            )
            self.assertTrue(created)
            self.assertEqual(forum_subcategory.forum_category, parent_category)
            self.assertEqual(forum_subcategory.type, ForumSubcategoryType.COHORT.name)
            self.assertEqual(forum_subcategory.course_forum_group, None)
            self.assertEqual(forum_subcategory.cohort_forum_group, cohort_forum_group)
            self.assertEqual(forum_subcategory.subcategory_id, 14)
