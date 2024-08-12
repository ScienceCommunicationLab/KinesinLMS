import logging
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.tests.factories import CourseFactory
from kinesinlms.forum.tests.factories import ForumCategoryFactory, ForumProviderFactory
from kinesinlms.users.tests.factories import UserFactory
from kinesinlms.users.tests.mixins import StaffOnlyTestMixin, SuperuserOnlyTestMixin
from kinesinlms.course.models import CourseCatalogDescription

logger = logging.getLogger(__name__)


class ComposerViewTestMixin:
    """
    Shared data/logic between all the composer view tests.
    """

    def setUp(self):
        super().setUp() # noqa
        self.course = CourseFactory()
        self.staff = UserFactory(is_staff=True)
        self.superuser = UserFactory(is_staff=True, is_superuser=True)


class CourseUpdateMixin(ComposerViewTestMixin, SuperuserOnlyTestMixin):
    """
    Shared logic between all the composer course update view tests.
    """

    def test_course_get_no_name(self):
        self.course.display_name = ""
        self.course.save()

        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, "Edit Course : ( no name )")


class TestComposerViews(ComposerViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()

    def test_home(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("composer:home"))
        self.assertContains(response, "Composer")
        self.assertContains(response, self.course.token)

    def test_courses(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("composer:course_list"))
        self.assertContains(response, "Course List")
        self.assertContains(response, "Create New Course")
        self.assertContains(response, self.course.token)


class TestCourseCreateView(ComposerViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("composer:course_create")

    def test_create_course(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, "Create a new course")

        course_data = {
            "display_name": "Course X",
            "slug": "XYZ",
            "run": "2",
            "self_paced": "on",
        }

        response = self.client.post(self.url, data=course_data)
        assert response.status_code == 302
        assert "settings" in response.headers["location"]

    def test_create_course_superuser_only(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        assert response.status_code == 403

        response = self.client.post(self.url)
        assert response.status_code == 403


class TestCourseEditView(ComposerViewTestMixin, StaffOnlyTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("composer:course_edit", kwargs={"course_id": self.course.id})

    def test_edit_course_get(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, f"Edit Course : {self.course.display_name}")
        self.assertContains(response, "course-unit-edit-controls")

    def test_edit_course_bad_unit(self):
        unit_node_url = reverse(
            "composer:course_edit_unit_node",
            kwargs={"course_id": self.course.id, "unit_node_id": 1234, },
        )
        self.client.force_login(self.superuser)
        response = self.client.get(unit_node_url)
        assert response.status_code == 404


class TestCourseSettingsUpdateView(CourseUpdateMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            "composer:course_edit_settings", kwargs={"pk": self.course.id}
        )

    def test_update_course_get(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, f"Edit Course : {self.course.display_name}")

    def test_update_course(self):
        self.client.force_login(self.superuser)

        course_data = {
            "display_name": "Course X",
            "slug": "XYZ",
            "run": "2",
            "self_paced": "on",
        }

        response = self.client.post(self.url, data=course_data, follow=True)
        self.assertContains(response, "Edit Course : Course X")
        self.assertEqual(response.redirect_chain, [(self.url, 302)])


class TestCourseCatalogDescriptionUpdateView(CourseUpdateMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.course_edit_url = reverse(
            "composer:course_edit", kwargs={"course_id": self.course.id}
        )
        self.course_catalog_edit_url = reverse(
            "composer:course_catalog_description_edit",
            kwargs={
                "course_id": self.course.id,
                "pk": self.course.catalog_description.id,
            },
        )
        self.url = reverse(
            "composer:course_catalog_description_edit",
            kwargs={"course_id": self.course.id, "pk": self.course.id},
        )

    def test_update_catalog_get(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, f"Edit Course : {self.course.display_name}")

    def test_update_catalog(self):
        self.client.force_login(self.superuser)
        self.assertNotEqual(self.course.catalog_description.title, "NEW NAME")
        catalog_description_id = self.course.catalog_description.id

        course_data = {
            "about_content": "About this course..",
            "sidebar_content": "More resources available here..",
            "hex_theme_color": "e1e1e1",
            "hex_title_color": "ffffff",
            "order": 0,
            "title": "NEW NAME",
            "duration": "1 month",
            "blurb": "2",
            "visible": "on",
        }

        response = self.client.post(self.url, data=course_data, follow=True)
        self.assertEqual(response.redirect_chain, [(self.course_catalog_edit_url, 302)])
        catalog_description = CourseCatalogDescription.objects.get(id=catalog_description_id)
        self.assertEqual(catalog_description.title, "NEW NAME")


class TestCourseBadgesListView(CourseUpdateMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            "composer:course_badge_classes_list", kwargs={"course_id": self.course.id}
        )

    def test_course_badges_get(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, f"Edit Course : {self.course.display_name}")
        self.assertContains(response, "Course Badge Classes")


class TestCourseForumEditView(ComposerViewTestMixin, StaffOnlyTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            "composer:course_forum_edit", kwargs={"course_id": self.course.id}
        )

    def test_edit_forum_get(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, "Course Forum")
        self.assertContains(
            response,
            "No forum provider has been set up, so this course cannot be linked to a forum.",
        )

    def test_edit_forum_category_get(self):
        site = Site.objects.get_current()
        ForumProviderFactory(site=site)
        ForumCategoryFactory(course=self.course, category_slug="this-category")

        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, "Course Forum")
        self.assertNotContains(
            response,
            "No forum provider has been set up, so this course cannot be linked to a forum.",
        )


class TestComposerSettingsView(ComposerViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.student = UserFactory()
        self.url = reverse("composer:settings")

    # No composer settings page at the moment.
    # def test_composer_settings_get(self):
    #    self.client.force_login(self.staff)
    #    response = self.client.get(self.url)
    #    self.assertContains(response, "Html edit mode")

    def test_composer_settings_post(self):
        self.client.force_login(self.staff)
        data = {
            "html_edit_mode": "TINY_MCE",
        }
        response = self.client.post(self.url, data=data, follow=True)
        self.assertContains(response, "Composer settings saved.")
        self.assertEqual(response.redirect_chain, [(self.url, 302)])

    def test_staff_or_superuser_only(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        assert response.status_code == 403

        response = self.client.post(self.url)
        assert response.status_code == 403
