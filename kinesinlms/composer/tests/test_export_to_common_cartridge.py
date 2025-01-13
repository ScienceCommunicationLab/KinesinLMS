import io
import logging
import shutil
import zipfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from lxml import etree

from kinesinlms.composer.import_export.common_cartridge.constants import (
    NAMESPACES,
    SCHEMA_LOCATIONS,
    CommonCartridgeExportDir,
)
from kinesinlms.composer.import_export.common_cartridge.exporter import (
    CommonCartridgeExporter,
)
from kinesinlms.composer.import_export.common_cartridge.resource import (
    CommonCartridgeResourceType,
    HTMLContentCCResource,
    VideoCCResource,
)
from kinesinlms.composer.import_export.common_cartridge.utils import validate_resource_path
from kinesinlms.core.utils import get_current_site_profile
from kinesinlms.course.models import Course
from kinesinlms.course.tests.factories import CourseFactory, CourseUnitFactory
from kinesinlms.learning_library.models import BlockResource, BlockType, Resource, ResourceType
from kinesinlms.learning_library.tests.factories import BlockFactory, UnitBlockFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = "/api/bookmarks/"


class TestComposerCourseExportToCommonCartridge(TestCase):
    """
    Test that we can export a course to Common Cartridge format.
    """

    def setUp(self):
        course: Course = CourseFactory.create()
        self.course_base_url = course.course_url
        self.course = course

        site_profile = get_current_site_profile()
        site_profile.institution_name = "Test Institution"
        site_profile.save()

        User = get_user_model()
        self.admin_user = User.objects.create(username="daniel", is_staff=True, is_superuser=True)

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

    def test_create_manifest_root_el(self):
        """
        Test that we can create the root element of the manifest file.
        """
        exporter = CommonCartridgeExporter()
        manifest = exporter._create_manifest_root_el(self.course)

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
                f"Namespace {prefix} has incorrect value. " f"Expected {uri}, got {actual_uri}",
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

    def test_create_metadata_el(self):
        """
        Test that we can create the metadata element with all required sub-elements
        for the Common Cartridge export.
        """
        exporter = CommonCartridgeExporter()
        metadata = exporter._create_metadata_el(self.course)

        # Check it's an lxml Element
        self.assertIsInstance(metadata, etree._Element)

        # Check basic structure
        self.assertEqual(metadata.tag, "metadata")

        # Check schema element
        schema = metadata.find("schema")
        self.assertIsNotNone(schema)
        self.assertEqual(schema.text, "IMS Common Cartridge")

        # Check schema version
        schema_version = metadata.find("schemaversion")
        self.assertIsNotNone(schema_version)
        self.assertEqual(schema_version.text, "1.3.0")

        # Check LOM element and its children
        lom = metadata.find("lomimscc:lom", namespaces=NAMESPACES)
        self.assertIsNotNone(lom)

        # Check general section
        general = lom.find("lomimscc:general", namespaces=NAMESPACES)
        self.assertIsNotNone(general)

        # Check title
        title = general.find("lomimscc:title/lomimscc:string", namespaces=NAMESPACES)
        self.assertIsNotNone(title)
        self.assertEqual(title.get("language"), settings.LANGUAGE_CODE)
        self.assertEqual(title.text, self.course.display_name or "Untitled Course")

        # Check description
        description = general.find("lomimscc:description/lomimscc:string", namespaces=NAMESPACES)
        self.assertIsNotNone(description)
        self.assertEqual(description.get("language"), settings.LANGUAGE_CODE)
        self.assertEqual(description.text, self.course.overview)

        # Check language
        language = general.find("lomimscc:language", namespaces=NAMESPACES)
        self.assertIsNotNone(language)
        self.assertEqual(language.text, settings.LANGUAGE_CODE)

        # Check keywords if course has tags
        if self.course.tags.exists():
            keyword = general.find("lomimscc:keyword/lomimscc:string", namespaces=NAMESPACES)
            self.assertIsNotNone(keyword)
            self.assertEqual(keyword.get("language"), settings.LANGUAGE_CODE)
            expected_keywords = ",".join([tag.name for tag in self.course.tags.all()])
            self.assertEqual(keyword.text, expected_keywords)

        # Check lifecycle section
        lifecycle = lom.find("lomimscc:lifeCycle", namespaces=NAMESPACES)
        self.assertIsNotNone(lifecycle)

        # Check contribute section
        contribute = lifecycle.find("lomimscc:contribute", namespaces=NAMESPACES)
        self.assertIsNotNone(contribute)

        # Check role
        role = contribute.find("lomimscc:role/lomimscc:value", namespaces=NAMESPACES)
        self.assertIsNotNone(role)
        self.assertEqual(role.text, "Author")

        # Check entity
        entity = contribute.find("lomimscc:entity", namespaces=NAMESPACES)
        self.assertIsNotNone(entity)
        site_profile = get_current_site_profile()
        expected_entity = site_profile.institution_name or site_profile.uuid
        self.assertEqual(entity.text, expected_entity)

        # Check date
        date = contribute.find("lomimscc:date/lomimscc:dateTime", namespaces=NAMESPACES)
        self.assertIsNotNone(date)
        self.assertEqual(date.text, self.course.created_at.strftime("%Y-%m-%d"))

        # Check technical metadata
        technical = lom.find("lomimscc:technical", namespaces=NAMESPACES)
        self.assertIsNotNone(technical)
        format_el = technical.find("lomimscc:format", namespaces=NAMESPACES)
        self.assertIsNotNone(format_el)
        self.assertEqual(format_el.text, "text/html")

        # Check educational metadata
        educational = lom.find("lomimscc:educational", namespaces=NAMESPACES)
        self.assertIsNotNone(educational)
        resource_type = educational.find("lomimscc:learningResourceType/lomimscc:value", namespaces=NAMESPACES)
        self.assertIsNotNone(resource_type)
        self.assertEqual(resource_type.text, "Course")

        # Print the XML for visual inspection
        logger.info("All good! Here's what the metadata looks like:")
        xml_str = etree.tostring(
            metadata,
            encoding="unicode",
            pretty_print=True,
        )
        logger.info("\nGenerated XML:\n%s", xml_str)

    def test_create_organizations_el(self):
        """
        Test that we can create organization items that reflect our three-tier
        course structure (Module -> Section -> Unit -> Block).
        """
        exporter = CommonCartridgeExporter()
        organizations_el = exporter._create_organizations_el(self.course)

        # Check it's an lxml Element
        self.assertIsInstance(organizations_el, etree._Element)

        # Check organizations element
        self.assertEqual(organizations_el.tag, "organizations")
        self.assertEqual(organizations_el.get("default"), "org_1")

        # Check organization element
        organization_el = organizations_el.find("organization")
        self.assertIsNotNone(organization_el)
        self.assertEqual(organization_el.get("identifier"), "org_1")
        self.assertEqual(organization_el.get("structure"), "rooted-hierarchy")

        # Get the root item element
        items_el = organization_el.find("item")
        self.assertIsNotNone(items_el)
        self.assertEqual(items_el.get("identifier"), "course_root")
        self.assertEqual(items_el.get("isvisible"), "true")

        # Check course root title
        root_title = items_el.find("title")
        self.assertIsNotNone(root_title)
        self.assertEqual(root_title.text, self.course.display_name or "Course Content")

        # Check course root title
        root_title = items_el.find("title")
        self.assertIsNotNone(root_title)
        self.assertEqual(root_title.text, self.course.display_name or "Course Content")

        # Check module level exists
        for module_node in self.course.course_root_node.get_children():
            module_el = items_el.find(f"item[@identifier='module_{module_node.id}']")
            self.assertIsNotNone(module_el)
            self.assertEqual(module_el.get("isvisible"), "true")
            self.assertEqual(
                module_el.find("title").text,
                module_node.display_name or f"Module {module_node.order + 1}",
            )

            # Check section level exists within module
            for section_node in module_node.get_children():
                section_el = module_el.find(f"item[@identifier='section_{section_node.id}']")
                self.assertIsNotNone(section_el)
                self.assertEqual(section_el.get("isvisible"), "true")
                self.assertEqual(
                    section_el.find("title").text,
                    section_node.display_name or f"Section {section_node.order + 1}",
                )

                # Check unit level exists within section
                for unit_node in section_node.get_children():
                    unit_el = section_el.find(f"item[@identifier='unit_{unit_node.id}']")
                    self.assertIsNotNone(unit_el)
                    self.assertEqual(unit_el.get("isvisible"), "true")
                    self.assertEqual(
                        unit_el.find("title").text,
                        unit_node.display_name or f"Unit {unit_node.order + 1}",
                    )

                    # Check blocks exist within unit
                    for unit_block in unit_node.unit.unit_blocks.all():
                        block = unit_block.block
                        block_el = unit_el.find(f"item[@identifier='unit_block_{unit_block.id}']")
                        self.assertIsNotNone(block_el)
                        self.assertEqual(block_el.get("isvisible"), "true")
                        self.assertEqual(block_el.get("identifierref"), str(unit_block.id))
                        expected_export_title = block.display_name
                        self.assertEqual(
                            block_el.find("title").text,
                            expected_export_title,
                        )

        # Print the XML for visual inspection
        logger.info("All good! Here's what the organization items look like:")
        xml_str = etree.tostring(
            organizations_el,
            encoding="unicode",
            pretty_print=True,
        )
        logger.info("\nGenerated XML:\n%s", xml_str)

    def test_validate_resource_path(self):
        """Test the resource path validation functionality."""
        valid_paths = [
            "folder/file.html",
            "123e4567-e89b-12d3-a456-426614174000/content.html",
            "web_resources/image-123/test_image.jpg",
            "some-folder/another_folder/file-name.xml",
        ]

        invalid_paths = [
            "/absolute/path/file.html",  # starts with slash
            "folder//double-slash.html",  # consecutive slashes
            "folder/space file.html",  # contains space
            "folder/COM1/file.html",  # Windows reserved name
            "folder/../file.html",  # parent directory reference
            "folder/special@char.html",  # special characters
            "folder/PRN/test.html",  # Another Windows reserved name
        ]

        for path in valid_paths:
            self.assertTrue(validate_resource_path(path), f"Path should be valid: {path}")

        for path in invalid_paths:
            self.assertFalse(validate_resource_path(path), f"Path should be invalid: {path}")

    def test_block_resource_file_paths_validation(self):
        """
        Test that block resource file paths are properly slugified.
        """

        block = BlockFactory.create(
            display_name="Test .. Block",  # invalid characters - can't have ".."
            type=BlockType.HTML_CONTENT.name,
        )
        course_unit = CourseUnitFactory.create(
            course=self.course,
            slug="test-course-unit",
        )
        unit_block = UnitBlockFactory.create(block=block, course_unit=course_unit)

        # Test that the path generation and validation works
        handler = HTMLContentCCResource(unit_block=unit_block)
        path = handler._block_resource_file_path()
        self.assertEqual(path, f"{unit_block.block.uuid}/test-block.html", "Block display name should be slugified")

    def test_create_resources_el_with_validation(self):
        """
        Test <resource/> element creation with path validation.
        """
        exporter = CommonCartridgeExporter()
        course = self.course

        # Create test resources with various paths
        resources_el = exporter._create_cc_resources_el(course)

        # Test that all resource href attributes are valid paths
        for resource_el in resources_el.findall(".//resource"):
            href = resource_el.get("href")
            if href:  # Some resources might not have href
                self.assertTrue(validate_resource_path(href), f"Resource href should be valid: {href}")

            # Test nested file elements
            for file_el in resource_el.findall(".//file"):
                file_href = file_el.get("href")
                self.assertTrue(validate_resource_path(file_href), f"File href should be valid: {file_href}")

    def test_video_resource_type(self):
        """
        Test that video blocks get the correct CC resource type.
        when the <resource/> element is created.
        """

        block = BlockFactory.create(type=BlockType.VIDEO.name)
        course_unit = CourseUnitFactory.create(
            course=self.course,
            slug="test-course-unit",
        )
        unit_block = UnitBlockFactory.create(block=block, course_unit=course_unit)

        # Create handler and check resource type
        handler = VideoCCResource(unit_block=unit_block)
        self.assertEqual(
            handler.get_cc_resource_type(),
            CommonCartridgeResourceType.WEB_CONTENT.value,  # or WEB_LINK.value if changed
            "Video resource should use correct type",
        )

        # Test the created resource element
        resource_el = handler.create_cc_resource_element_for_unit_block()
        self.assertEqual(
            resource_el.get("type"),
            CommonCartridgeResourceType.WEB_CONTENT.value,  # or WEB_LINK.value if changed
            "Video resource element should have correct type",
        )

    def test_html_content_resource_paths(self):
        """

        Test that we can properly replace expected template tags
        with the correct resource paths in HTML content.

        """
        # Create HTML block with resources
        block = BlockFactory.create(
            type=BlockType.HTML_CONTENT.name,
            html_content="""<p>Some HTML here. Then an image tag <img src="{% block_resource_url 'test-image' %}"></p>""",
        )
        course_unit = CourseUnitFactory.create(
            course=self.course,
            slug="test-course-unit",
        )
        unit_block = UnitBlockFactory.create(block=block, course_unit=course_unit)

        # Add a resource
        resource_file_name = "test.jpg"
        resource = Resource.objects.create(
            type=ResourceType.IMAGE.name,
            slug="test-image",
            resource_file=SimpleUploadedFile(resource_file_name, b"file_content"),
        )
        BlockResource.objects.create(block=unit_block.block, resource=resource)

        # Create handler and process HTML
        handler = HTMLContentCCResource(unit_block=unit_block)
        processed_html = handler._reformat_html_content_with_relative_resource_file_paths(unit_block)

        # DMcQ: why does Django add an initial "\n" when rendering template?
        expected_html = f"""\n<p>Some HTML here. Then an image tag <img src="$IMS-CC-FILEBASE$/{resource.uuid}/{resource_file_name}"></p>"""

        # Verify the paths are properly formatted
        self.assertEqual(
            expected_html,
            processed_html,
            "HTML was not processed correctly",
        )
