import io
import logging
import shutil
import zipfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = '/api/bookmarks/'


class TestComposerCourseExportToCommonCartridge(TestCase):
    """
    Test that we can export a course to Common Cartridge format.
    """

    def setUp(self):
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        User = get_user_model()
        self.admin_user = User.objects.create(username="daniel",
                                              is_staff=True,
                                              is_superuser=True)

    def test_course_export(self):
        self.client.force_login(self.admin_user)
        course = self.course
        export_url = reverse('composer:course_download_export', kwargs={
            'course_slug': course.slug,
            'course_run': course.run
        })
        export_url = export_url + '?export_format=CC_FULL'
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)

        # TEMP: for visual inspection of export
        # unzip bytes in response.content and write to file so that I can review export quickly
        zip_content = io.BytesIO(response.content)
        export_dir = settings.BASE_DIR / 'tmp' / 'course_export'
        if export_dir.exists():
            shutil.rmtree(export_dir)

        with zipfile.ZipFile(zip_content, 'r') as zip_ref:
            export_dir.mkdir(parents=True, exist_ok=True)
            zip_ref.extractall(export_dir)
