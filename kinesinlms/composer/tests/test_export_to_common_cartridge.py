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
from kinesinlms.core.utils import get_current_site_profile
from kinesinlms.course.models import Course
from kinesinlms.course.tests.factories import CourseFactory

logger = logging.getLogger(__name__)

TRACKING_API_ENDPOINT = "/api/bookmarks/"


class TestComposerCourseExportToCommonCartridge(TestCase):
    """
    Test that we can export a course to Common Cartridge format.
    """

    def setUp(self):
        course: Course = CourseFactory()
        self.course_base_url = course.course_url
        self.course = course

        site_profile = get_current_site_profile()
        site_profile.institution_name = "Test Institution"
        site_profile.save()

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

    def test_create_metadata_xml(self):
        """
        Test that we can create the metadata element with all required sub-elements
        for the Common Cartridge export.
        """
        exporter = CommonCartridgeExporter()
        metadata = exporter._create_metadata_xml(self.course)

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
        description = general.find(
            "lomimscc:description/lomimscc:string", namespaces=NAMESPACES
        )
        self.assertIsNotNone(description)
        self.assertEqual(description.get("language"), settings.LANGUAGE_CODE)
        self.assertEqual(description.text, self.course.overview)

        # Check language
        language = general.find("lomimscc:language", namespaces=NAMESPACES)
        self.assertIsNotNone(language)
        self.assertEqual(language.text, settings.LANGUAGE_CODE)

        # Check keywords if course has tags
        if self.course.tags.exists():
            keyword = general.find(
                "lomimscc:keyword/lomimscc:string", namespaces=NAMESPACES
            )
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
        resource_type = educational.find(
            "lomimscc:learningResourceType/lomimscc:value", namespaces=NAMESPACES
        )
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

    def test_create_organizations_xml(self):
        """
        Test that we can create organization items that reflect our three-tier
        course structure (Module -> Section -> Unit -> Block).
        """
        exporter = CommonCartridgeExporter()
        organizations_el = exporter._create_organizations_xml(self.course)

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
                section_el = module_el.find(
                    f"item[@identifier='section_{section_node.id}']"
                )
                self.assertIsNotNone(section_el)
                self.assertEqual(section_el.get("isvisible"), "true")
                self.assertEqual(
                    section_el.find("title").text,
                    section_node.display_name or f"Section {section_node.order + 1}",
                )

                # Check unit level exists within section
                for unit_node in section_node.get_children():
                    unit_el = section_el.find(
                        f"item[@identifier='unit_{unit_node.id}']"
                    )
                    self.assertIsNotNone(unit_el)
                    self.assertEqual(unit_el.get("isvisible"), "true")
                    self.assertEqual(
                        unit_el.find("title").text,
                        unit_node.display_name or f"Unit {unit_node.order + 1}",
                    )

                    # Check blocks exist within unit
                    for unit_block in unit_node.unit.unit_blocks.all():
                        block = unit_block.block
                        block_el = unit_el.find(
                            f"item[@identifier='block_{block.uuid}']"
                        )
                        self.assertIsNotNone(block_el)
                        self.assertEqual(block_el.get("isvisible"), "true")
                        self.assertEqual(block_el.get("identifierref"), str(block.uuid))
                        self.assertEqual(
                            block_el.find("title").text,
                            block.display_name or block.type,
                        )

        # Print the XML for visual inspection
        logger.info("All good! Here's what the organization items look like:")
        xml_str = etree.tostring(
            organizations_el,
            encoding="unicode",
            pretty_print=True,
        )
        logger.info("\nGenerated XML:\n%s", xml_str)
