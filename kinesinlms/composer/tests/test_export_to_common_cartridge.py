import io
import logging
import shutil
import zipfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from lxml import etree

from kinesinlms.composer.import_export.constants import NAMESPACES, SCHEMA_LOCATIONS
from kinesinlms.composer.import_export.exporter import CommonCartridgeExporter
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = "/api/bookmarks/"


class TestComposerCourseExportToCommonCartridge(TestCase):
    """
    Test that we can export a course to Common Cartridge format.
    """

    def setUp(self):
        course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        User = get_user_model()
        self.admin_user = User.objects.create(
            username="daniel", is_staff=True, is_superuser=True
        )

    def test_course_export(self):
        self.client.force_login(self.admin_user)
        course = self.course
        export_url = reverse(
            "composer:course_download_export",
            kwargs={"course_slug": course.slug, "course_run": course.run},
        )
        export_url = export_url + "?export_format=CC_FULL"
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)

        # TEMP: for visual inspection of export
        # unzip bytes in response.content and write to file so that I can review export quickly
        zip_content = io.BytesIO(response.content)
        export_dir = settings.BASE_DIR / "tmp" / "course_export"
        if export_dir.exists():
            shutil.rmtree(export_dir)

        with zipfile.ZipFile(zip_content, "r") as zip_ref:
            export_dir.mkdir(parents=True, exist_ok=True)
            zip_ref.extractall(export_dir)

    # Test individual methods of CommonCartridgeExporter
    # ..........................................................

    def test_create_manifest_root_element(self):
        """
        Test that we can create the root element of the manifest file.
        """
        exporter = CommonCartridgeExporter()
        manifest = exporter._create_manifest_root_element(self.course)

        # Check it's an lxml Element
        self.assertIsInstance(manifest, etree._Element)

        # Check basic attributes
        self.assertEqual(manifest.tag, "manifest")
        self.assertEqual(manifest.get("identifier"), "TEST_SP")
        self.assertEqual(manifest.get("version"), "1.3.0")

        # Check all required namespaces are present
        # lxml stores namespaces in the nsmap property
        for prefix, uri in NAMESPACES.items():
            if prefix:
                actual_uri = manifest.nsmap.get(prefix)
            else:
                actual_uri = manifest.nsmap.get(None)  # Default namespace
            self.assertEqual(
                actual_uri,
                uri,
                f"Namespace {prefix} has incorrect value. "
                f"Expected {uri}, got {actual_uri}",
            )

        # Check schema location using lxml's QName
        schema_location = manifest.get(etree.QName(NAMESPACES["xsi"], "schemaLocation"))
        self.assertIsNotNone(schema_location)

        # Verify all required schema locations are present
        schema_parts = schema_location.split()
        for schema_location_name in SCHEMA_LOCATIONS:
            self.assertIn(
                schema_location_name,
                schema_parts,
                f"Missing schema location: {schema_location_name}",
            )

        # Pretty print the XML with lxml's built-in pretty printing
        logger.info("All good! Here's what the manifest looks like:")
        xml_str = etree.tostring(
            manifest,
            encoding="unicode",  # Get string output
            pretty_print=True,
        )
        logger.info("\nGenerated XML:\n%s", xml_str)  # Using %s formatting for logger
