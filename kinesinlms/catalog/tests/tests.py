from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from kinesinlms.course.models import Enrollment
from kinesinlms.course.tests.factories import CourseFactory


class TestCourseCatalogDescription(TestCase):
    enrolled_user = None
    course = None

    @classmethod
    def setUpTestData(cls):
        super(TestCourseCatalogDescription, cls).setUpTestData()
        User = get_user_model()
        cls.new_user = User.objects.create(username="new-user")
        cls.enrolled_user = User.objects.create(username="enrolled-user")
        cls.admin_user = User.objects.create(username="daniel",
                                             is_staff=True,
                                             is_superuser=True)

        course = CourseFactory()
        cls.course = course

        Enrollment.objects.get_or_create(student=cls.enrolled_user,
                                         course=cls.course,
                                         active=True)

    def test_index(self):
        catalog_url = reverse('catalog:index')
        response = self.client.get(catalog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_about_page(self):
        about_page_url = reverse('catalog:about_page', kwargs={
            'course_slug': self.course.slug,
            'course_run': self.course.run
        })
        response = self.client.get(about_page_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_enroll_user_in_course(self):
        self.client.force_login(self.new_user)
        # make sure student not yet enrolled
        self.assertEqual(0, Enrollment.objects.filter(course=self.course, student=self.new_user).count())

        enroll_url = reverse('catalog:enroll', kwargs={
            'course_slug': self.course.slug,
            'course_run': self.course.run
        })
        response = self.client.post(enroll_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        # Test passes if we don't get an exception here...
        Enrollment.objects.get(course=self.course, student=self.new_user)
