import logging
from io import BytesIO
from typing import Optional
from zipfile import ZipFile

from django.conf import settings
from lxml import etree
from lxml.etree import register_namespace

from kinesinlms.composer.import_export.common_cartridge.constants import (
    NAMESPACES,
    SCHEMA_LOCATIONS,
    CommonCartridgeExportFormat,
)
from kinesinlms.composer.import_export.common_cartridge.factory import (
    CCHandlerFactory,
)
from kinesinlms.composer.import_export.common_cartridge.resource import CCHandler
from kinesinlms.composer.import_export.exporter import BaseExporter
from kinesinlms.core.utils import get_current_site_profile
from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)


class CommonCartridgeExporter(BaseExporter):
    """
    Exports a course to Common Cartridge format.
    At the moment that means version 1.3.
    """

    def __init__(self):
        self._setup_namespaces_and_prefixes()
        self.resource_factory = CCHandlerFactory()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def export_course(self, course: Course, export_format) -> BytesIO:
        """
        Build and return a Common Cartridge export of the given course.
        A common cartridge export is a zip file containing:
            -   An imsmanifest.xml file
            -   A 'Resources Directory' folder of web resources (HTML, images, etc.)
                used by the course
            -   May include a 'META-INF' folder with additional metadata.

        Args:
            course (Course): The course to export
            export_format (string): The CommonCartridgeExportFormat to use

        Raises:
            ValueError: if arguments are invalid
            Exception: if an error occurs during export


        Returns:
            BytesIO: A BytesIO object containing the Common Cartridge export.
            This is effectively a zip file.
        """

        if not course:
            raise ValueError("Course must be specified for export.")
        if export_format not in [item.name for item in CommonCartridgeExportFormat]:
            raise ValueError(f"Export format {export_format} not supported.")

        # XML STUFF
        # ............................................................................
        # Create a zip to hold various parts of the cartridge
        bytes_io = BytesIO()
        zf = ZipFile(bytes_io, "w")

        # Create the imsmanifest.xml file...
        try:
            manifest_xml: etree.Element = self._create_ims_manifest_xml(course)
        except Exception as e:
            logger.error(f"Error creating manifest: {e}")
            raise e

        # Serialize the XML tree to a string
        try:
            xml_str = etree.tostring(
                manifest_xml,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )
        except Exception as e:
            logger.error(f"Error serializing manifest to string: {e}")
            raise e

        try:
            zf.writestr("imsmanifest.xml", xml_str)
        except Exception as e:
            logger.error(f"Error writing manifest to zip file: {e}")
            raise e

        # FILE STUFF
        # ............................................................................
        # Create "resource" files and add to zip.
        try:
            self._create_resource_files(course=course, zip_file=zf)
        except Exception as e:
            logger.error(f"Error creating resource files: {e}")
            raise e

        # Return the zip file
        zf.close()
        return bytes_io

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _setup_namespaces_and_prefixes(self):
        # Register all namespace prefixes with etree
        for prefix, uri in NAMESPACES.items():
            if prefix:
                register_namespace(prefix, uri)

    def _create_ims_manifest_xml(self, course: Course) -> etree.Element:
        """
        Create the imsmanifest XML (element) for the Common Cartridge export.

        Args:
            course (Course): The course to export

        Returns:
            Element: The root <manifest/> element for the course, complete with nested
            <metadata/>, <resources/>, and <organizations/> elements.

        """
        manifest_el: etree.Element = self._create_manifest_root_el(course=course)

        metadata_el: etree.Element = self._create_metadata_el(course=course)
        manifest_el.append(metadata_el)

        organizations_el: etree.Element = self._create_organizations_el(course=course)
        manifest_el.append(organizations_el)

        resources_el: etree.Element = self._create_cc_resources_el(course=course)
        manifest_el.append(resources_el)

        return manifest_el

    def _create_manifest_root_el(self, course) -> etree.Element:
        """
        Create the root <manifest/> element for the Common Cartridge export.
        We need to add a bunch of namespaces to the root element.

        Returns:
            The <manifest/> element for the course, complete with namespaces.

        """

        # Create manifest element with basic attributes
        manifest_el = etree.Element(
            "manifest",
            attrib={
                "identifier": course.token,
                "version": "1.3.0",
            },
            nsmap=NAMESPACES,
        )

        # Add schema location after namespaces
        # Note: The weird triple-brace syntax expands to something like
        # "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
        # This format is how ElementTree represents namespaced attributes internally using
        # {namespace-uri}localname
        schema_locations = " ".join(SCHEMA_LOCATIONS)
        manifest_el.set(etree.QName(NAMESPACES["xsi"], "schemaLocation"), schema_locations)
        return manifest_el

    def _create_metadata_el(self, course: Course) -> etree.Element:
        """
        Create the metadata element for the Common Cartridge export.
        Populate with metadata about the course.

        Returns:
            The <metadata/> element for the course, complete with nested
            <lomimscc:lom> element.
        """
        metadata_el = etree.Element("metadata")

        schema_el = etree.Element("schema")
        schema_el.text = "IMS Common Cartridge"
        metadata_el.append(schema_el)

        schemaversion_el = etree.Element("schemaversion")
        schemaversion_el.text = "1.3.0"
        metadata_el.append(schemaversion_el)

        lom_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "lom"))

        general_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "general"))

        # Add title
        title_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "title"))
        title_en_el = etree.Element(
            etree.QName(NAMESPACES["lomimscc"], "string"),
            attrib={"language": settings.LANGUAGE_CODE},
        )
        title_en_el.text = course.display_name or "Untitled Course"
        title_el.append(title_en_el)
        general_el.append(title_el)

        # Add description. We'll use the course overview.
        description_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "description"))
        description_string_el = etree.Element(
            etree.QName(NAMESPACES["lomimscc"], "string"),
            attrib={"language": settings.LANGUAGE_CODE},
        )
        description_string_el.text = course.overview
        description_el.append(description_string_el)
        general_el.append(description_el)

        # Add language
        language_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "language"))
        language_el.text = settings.LANGUAGE_CODE
        general_el.append(language_el)

        # Add keywords if available
        if course.tags.exists():
            keyword_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "keyword"))
            keyword_string_el = etree.Element(
                etree.QName(NAMESPACES["lomimscc"], "string"),
                attrib={"language": settings.LANGUAGE_CODE},
            )
            keyword_string_el.text = ",".join([tag.name for tag in course.tags.all()])
            keyword_el.append(keyword_string_el)
            general_el.append(keyword_el)

        lom_el.append(general_el)

        lifecycle_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "lifeCycle"))
        contribute_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "contribute"))

        # Add role
        role_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "role"))
        source_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "source"))
        source_el.text = "LOMv1.0"
        role_el.append(source_el)
        value_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "value"))
        value_el.text = "Author"
        role_el.append(value_el)
        contribute_el.append(role_el)

        # Add entity (creator info)
        site_profile = get_current_site_profile()
        entity_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "entity"))
        if site_profile.institution_name:
            entity_el.text = site_profile.institution_name
        else:
            entity_el.text = str(site_profile.uuid)
        contribute_el.append(entity_el)

        # Technical metadata
        technical_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "technical"))
        format_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "format"))
        format_el.text = "text/html"
        technical_el.append(format_el)
        lom_el.append(technical_el)

        # Educational metadata
        educational_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "educational"))
        learning_resource_type_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "learningResourceType"))
        value_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "value"))
        value_el.text = "Course"
        learning_resource_type_el.append(value_el)
        educational_el.append(learning_resource_type_el)
        lom_el.append(educational_el)

        date_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "date"))
        dateTime_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "dateTime"))
        dateTime_el.text = course.created_at.strftime("%Y-%m-%d")
        date_el.append(dateTime_el)
        contribute_el.append(date_el)
        lifecycle_el.append(contribute_el)
        lom_el.append(lifecycle_el)
        rights_el = self._get_rights_el(course=course)
        lom_el.append(rights_el)

        metadata_el.append(lom_el)

        return metadata_el

    def _get_rights_el(self, course) -> etree.Element:
        """
        Create the <rights/> element for the Common Cartridge export.

        Returns:
            The <lomimscc:rights/> element for the course, complete with nested
            <lomimscc:copyrightAndOtherRestrictions/> and <lomimscc:description/> elements.
        """
        rights_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "rights"))

        copyrightAndOtherRestrictions_el = etree.Element(
            etree.QName(NAMESPACES["lomimscc"], "copyrightAndOtherRestrictions")
        )
        value_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "value"))
        value_el.text = "yes"
        copyrightAndOtherRestrictions_el.append(value_el)
        rights_el.append(copyrightAndOtherRestrictions_el)

        license_text = course.content_license
        if not license_text:
            license_text = "( no license defined )"

        description_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "description"))
        description_text_el = etree.Element(etree.QName(NAMESPACES["lomimscc"], "string"))
        description_text_el.text = license_text
        description_el.append(description_text_el)
        rights_el.append(description_el)

        return rights_el

    def _create_organizations_el(self, course: Course) -> etree.Element:
        """
        Create the required <organizations/> element for the Common Cartridge export.

        Not sure when we'll ever need more than one <organization/> for a CC export,
        but it is supported by standard.

        Returns:
            The <organizations/> element for the course, complete
            with an <organization/> element with nested structure of
            <item/> elements.

        """

        organizations_el = etree.Element("organizations", attrib={"default": "org_1"})
        organization_el: etree.Element = etree.Element(
            "organization",
            attrib={
                "identifier": "org_1",
                "structure": "rooted-hierarchy",
            },
        )
        organizations_el.append(organization_el)
        root_item_el = self._create_organization_tree(course=course)
        organization_el.append(root_item_el)

        return organizations_el

    def _create_organization_tree(self, course: Course) -> etree.Element:
        """
        Create the nested <item/> elements for the current course.
        Implements a three-tier structure:
        - Modules: Top level organization units
        - Sections: Groups of related units within a module
        - Units: Individual learning units containing blocks

        Returns:
            The root <item/> element for the course content.
        """
        # Create root item (required by spec to have single root)
        root_item_el = etree.Element(
            "item",
            attrib={
                "identifier": "course_root",
                "isvisible": "true",
            },
        )
        root_title = etree.Element("title")
        root_title.text = course.display_name or "Course Content"
        root_item_el.append(root_title)

        # Create Module level
        for m_idx, module_node in enumerate(course.course_root_node.get_children()):
            module_el = etree.Element(
                "item",
                attrib={
                    "identifier": f"module_{module_node.id}",
                    "isvisible": "true",
                },
            )
            module_title = etree.Element("title")
            module_title.text = module_node.display_name or f"Module {m_idx + 1}"
            module_el.append(module_title)
            root_item_el.append(module_el)

            # Create Section level within each Module
            for s_idx, section_node in enumerate(module_node.get_children()):
                section_el = etree.Element(
                    "item",
                    attrib={
                        "identifier": f"section_{section_node.id}",
                        "isvisible": "true",
                    },
                )
                section_title = etree.Element("title")
                section_title.text = section_node.display_name or f"Section {s_idx + 1}"
                section_el.append(section_title)
                module_el.append(section_el)

                # Create Unit level within each Section
                for u_idx, unit_node in enumerate(section_node.get_children()):
                    unit_el = etree.Element(
                        "item",
                        attrib={
                            "identifier": f"unit_{unit_node.id}",
                            "isvisible": "true",
                        },
                    )
                    unit_title = etree.Element("title")
                    unit_title.text = unit_node.display_name or f"Unit {u_idx + 1}"
                    unit_el.append(unit_title)
                    section_el.append(unit_el)

                    # Add UnitBlocks within each Unit
                    for unit_block in unit_node.unit.unit_blocks.all():
                        block = unit_block.block
                        unit_block_el = etree.Element(
                            "item",
                            attrib={
                                "identifier": f"unit_block_{unit_block.id_for_cc}",
                                "identifierref": unit_block.id_for_cc,
                                "isvisible": "true",
                            },
                        )
                        block_title = etree.Element("title")
                        block_title.text = block.display_name  # Okay to be None
                        unit_block_el.append(block_title)
                        unit_el.append(unit_block_el)

        return root_item_el

    # RESOURCES
    # Methods for creating <resources/> elements as well as adding
    # resource files to the zip.

    # Note that in CommonCatridge a "resource" is any file or URL that is
    # part of the course content.
    # Therefore, both Block instances as well as Resource instances are
    # considered "resources" in CC.

    def _create_cc_resources_el(self, course) -> etree.Element:
        """
        Use the CCHandler factory to create the required <resources/> elements
        for the Common Cartridge export. This means creating a <resource/> element
        for each Block, as well as all the Resources associated with those Blocks.

        This method makes sure not to write the same Resource to the manifest more than once.

        Returns:
            The <resources/> element for the course, complete with nested
            <resource/> elements for each resource used in the course.

        """
        resources_el = etree.Element("resources")
        # Keep track of which Resource objects we've already written to the manifest
        expoted_resource_ids = []
        for module_node in course.course_root_node.get_children():
            for section_node in module_node.get_children():
                for unit_node in section_node.get_children():
                    for unit_block in unit_node.unit.unit_blocks.all():
                        # Create a handler from our factory
                        ccr: Optional[CCHandler] = self.resource_factory.create_cc_handler(unit_block=unit_block)
                        if not ccr:
                            logger.info(f"  - SKIPPING unsupported block type: " f"{unit_block.block.type}")
                            continue
                        # UNIT BLOCK: Create the <resource/> element for this UnitBlock.
                        resource_el: etree.Element = ccr.create_cc_resource_element_for_unit_block()
                        resources_el.append(resource_el)

                        # BLOCK RESOURCE: Create the <resource/> elements for BlockResource items.
                        for block_resource in unit_block.block.block_resources.all():
                            # Only write each Resource once
                            if block_resource.resource.id in expoted_resource_ids:
                                continue
                            block_resource_el = ccr.create_cc_resource_element_for_block_related_resource(
                                block_resource=block_resource
                            )
                            resources_el.append(block_resource_el)
                            expoted_resource_ids.append(block_resource.resource.id)

        return resources_el

    def _create_resource_files(
        self,
        course: Course,
        zip_file: ZipFile,
    ) -> bool:
        """
        Create the resource files for the Common Cartridge export.
        These are added directly to the zip file.

        Args:
            course (Course): The course to export
            zip_file (ZipFile): The zip file to write to

        Returns:
            bool: True if successful, other Exception is raised
        """
        exported_resource_ids = []
        for module_node in course.course_root_node.get_children():
            for section_node in module_node.get_children():
                for unit_node in section_node.get_children():
                    for unit_block in unit_node.unit.unit_blocks.all():
                        block: Block = unit_block.block

                        # Write the Block resource file in the zip
                        resource_handler: Optional[CCHandler] = self.resource_factory.create_cc_handler(
                            unit_block=unit_block
                        )
                        if not resource_handler:
                            logger.info(f"  - SKIPPING unsupported block type: {block.type}")
                            continue

                        try:
                            resource_handler.create_cc_file_for_unit_block(
                                zip_file=zip_file,
                            )
                        except Exception as e:
                            logger.exception(f"Error creating resource file for " f"block {block.uuid}: {e}")
                            raise e

                        # Resource objects are linked in a many-to-many relationship
                        # to Blocks, so we only have to write each resource file once.
                        for block_resource in block.block_resources.all():
                            if block_resource.resource.id not in exported_resource_ids:
                                resource_handler.create_cc_file_for_block_related_resource(
                                    block_resource=block_resource,
                                    zip_file=zip_file,
                                )
                                exported_resource_ids.append(block_resource.resource.id)

        return True
