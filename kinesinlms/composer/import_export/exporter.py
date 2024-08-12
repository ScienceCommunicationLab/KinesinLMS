import datetime
import logging
import re
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Dict, Optional
from xml.etree.ElementTree import Element, ElementTree, indent
from zipfile import ZipFile

import pytz
from django.conf import settings
from lxml.etree import register_namespace
from rest_framework.renderers import JSONRenderer
from slugify import slugify

from kinesinlms.composer.import_export.config import EXPORT_DOCUMENT_TYPE, EXPORTER_VERSION
from kinesinlms.composer.import_export.constants import CourseExportFormat, CommonCartridgeExportFormat
from kinesinlms.course.models import Course, CourseUnit, CourseNode
from kinesinlms.course.serializers import CourseSerializer
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import BlockResource, Resource, UnitBlock

logger = logging.getLogger(__name__)


class BaseExporter(ABC):

    @abstractmethod
    def export_course(self, course: Course, export_format: str) -> BytesIO:
        raise NotImplementedError("Subclasses must implement this method.")


class CourseExporter(BaseExporter):
    """
    Exports a course to a standard KinesinLMS format.
    """

    def export_course(self, course: Course, export_format: str) -> BytesIO:
        """
        Exports a course to a JSON format.
        """
        if not course:
            raise ValueError("Course must be specified for export.")
        if not export_format:
            raise ValueError("Export format must be specified.")
        if export_format not in [item.name for item in CourseExportFormat]:
            raise ValueError(f"Export format {export_format} not supported.")

        if export_format == CourseExportFormat.KINESIN_LMS_ZIP.name:
            return self.export_course_to_zip(course)

    def export_course_to_zip(self, course: Course) -> BytesIO:
        """
        Exports a course to a zip file, including a file describing the course
        structure and files for all resources used by the course.

        Args:
            course:             Course to export

        Returns:
            BytesIO containing the zip file

        """
        if course is None:
            raise ValueError("Course must be specified for export.")

        # Write course.json to the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        bytes_io = BytesIO()
        zf = ZipFile(bytes_io, "w")
        course_json = self._serialize_course(course)
        zf.writestr("course.json", course_json)

        # Write generic resources to the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if bool(course.catalog_description.thumbnail):
            try:
                base_filename = course.catalog_description.thumbnail.name.split("/")[-1]
                full_internal_path = course.catalog_description.thumbnail.path
                export_file_path = f"catalog_resources/thumbnail/{base_filename}"
                zf.write(full_internal_path, export_file_path)
                logger.info(f"  - exported catalog thumbnail to {export_file_path}")
            except Exception as e:
                logger.error(f"Error writing catalog thumbnail to zip file: {e}")
                raise e
        
        if bool(course.catalog_description.syllabus):
            try:
                base_filename = course.catalog_description.syllabus.name.split("/")[-1]
                full_internal_path = course.catalog_description.syllabus.path
                export_file_path = f"catalog_resources/syllabus/{base_filename}"
                zf.write(full_internal_path, export_file_path)
                logger.info(f"  - exported catalog syllabus to {export_file_path}")
            except Exception as e:
                logger.error(f"Error writing catalog syllabus to zip file: {e}")
                raise e

        # Write block resources to the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Gather all Resources for this course via BlockResource
        resources: Dict[str, Resource] = {}
        course_units = CourseUnit.objects.filter(course=course).prefetch_related("contents")
        for course_unit in course_units:
            for block in course_unit.contents.all():
                for resource in block.resources.all():
                    if resource.uuid not in resources:
                        resources[resource.uuid] = resource
        # Write each Resource to the zip file.
        for uuid, resource in resources.items():
            try:
                base_filename = resource.resource_file.name.split("/")[-1]
                full_internal_path = resource.resource_file.path
                export_file_path = f"block_resources/{resource.type.upper()}/{resource.uuid}/{base_filename}"
                zf.write(full_internal_path, export_file_path)
            except Exception as e:
                logger.error(f"Error writing resource {resource.uuid} to zip file: {e}")
                raise e

        # Write course resources to zip file
        if hasattr(course, "course_resources"):
            for course_resource in course.course_resources.all():
                try:
                    base_filename = course_resource.resource_file.name.split("/")[-1]
                    full_internal_path = course_resource.resource_file.path
                    export_file_path = f"course_resources/{course_resource.uuid}/{base_filename}"
                    zf.write(full_internal_path, export_file_path)
                except Exception as e:
                    logger.error(f"Error writing course resource {course_resource.uuid} to zip file: {e}")
                    raise e

        # Finish writing the zip file.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        zf.close()

        return bytes_io

    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _serialize_course(self, course: Course) -> str:
        """
        Serializes top-level course information, including
        course 'description' information for the catalog.

        Args:
            course:     Course to serializer

        Returns:
            Serialized course in json string.
        """

        if course is None:
            raise ValueError("Course must be specified for export.")

        course_data = CourseSerializer(course).data

        course_serialized = {
            "document_type": EXPORT_DOCUMENT_TYPE,
            "metadata": {
                "exporter_version": EXPORTER_VERSION,
                "export_date": datetime.datetime.now(tz=pytz.utc).isoformat()
            },
            "course": course_data
        }

        course_json = JSONRenderer().render(course_serialized, renderer_context={'indent': 4})
        return course_json


class CommonCartridgeExporter(BaseExporter):
    """
    Exports a course to Common Cartridge format.
    At the moment that means version 1.3.
    """

    # Constants used to reference BlockResource files in the Common Cartridge export
    WEB_RESOURCES_DIR = 'web_resources/'
    IMS_CC_ROOT_DIR = '$IMS-CC-FILEBASE$/'

    def __init__(self):
        self._setup_namespaces_and_prefixes()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def export_course(self, course: Course, export_format) -> BytesIO:

        if not course:
            raise ValueError("Course must be specified for export.")
        if export_format not in [item.name for item in CommonCartridgeExportFormat]:
            raise ValueError(f"Export format {export_format} not supported.")

        # Create a zip to hold various parts of the cartridge
        bytes_io = BytesIO()
        zf = ZipFile(bytes_io, "w")

        # CREATE MANIFEST
        try:
            manifest_xml: Element = self._create_manifest(course)
            xml_tree = ElementTree(manifest_xml)

            # Set indentation for pretty printing
            indent(xml_tree)

        except Exception as e:
            logger.error(f"Error creating manifest: {e}")
            raise e

        try:
            mf = BytesIO()
            xml_tree.write(mf, encoding='utf-8', xml_declaration=True)
            zf.writestr("imsmanifest.xml", mf.getvalue())
        except Exception as e:
            logger.error(f"Error writing manifest to zip file: {e}")
            raise e

        # CREATE COURSE RESOURCE FILES
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

    def _create_resource_files(self, course: Course, zip_file: ZipFile):
        """
        Create the resource files for the Common Cartridge export.
        """
        for module_node in course.course_root_node.get_children():
            for section_node in module_node.get_children():
                for unit_node in section_node.get_children():
                    for unit_block in unit_node.unit.unit_blocks.all():
                        self._create_block_resource_file(module_node=module_node,
                                                         unit_block=unit_block,
                                                         zip_file=zip_file)

                        for block_resource in unit_block.block.block_resources.all():
                            self._create_block_related_file(block_resource=block_resource,
                                                            zip_file=zip_file)

        return True

    def _create_block_resource_file(self,
                                    module_node: CourseNode,
                                    unit_block: UnitBlock,
                                    zip_file: ZipFile) -> bool:
        """
        Create the required resource file for the given block in the Common Cartridge export zip.
        """
        block = unit_block.block

        # TODO: Create a builder for representing each
        #   block type as a string of 'simple' HTML content that
        #   allows stand alone rendering of the block content.
        if block.type == BlockType.HTML_CONTENT.name:
            result = self._create_html_block_resource_file(module_node=module_node,
                                                           unit_block=unit_block,
                                                           zip_file=zip_file)
        elif block.type == BlockType.VIDEO.name:
            result = self._create_video_block_resource_file(module_node=module_node,
                                                            unit_block=unit_block,
                                                            zip_file=zip_file)
        elif block.type == BlockType.ASSESSMENT.name:
            result = self._create_assessment_block_resource_file(module_node=module_node,
                                                                 unit_block=unit_block,
                                                                 zip_file=zip_file)
        elif block.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
            result = self._create_sit_block_resource_file(module_node=module_node,
                                                          unit_block=unit_block,
                                                          zip_file=zip_file)
        elif block.type == BlockType.FORUM_TOPIC.name:
            result = self._create_forum_topic_block_resource_file(module_node=module_node,
                                                                  unit_block=unit_block,
                                                                  zip_file=zip_file)

        else:
            logger.info(f"Block type not supported for export: {block.type}")
            result = False

        return result

    def _create_forum_topic_block_resource_file(self,
                                                module_node: CourseNode,            # noqa: F841
                                                unit_block: UnitBlock,              # noqa: F841
                                                zip_file: ZipFile) -> bool:         # noqa: F841
        """
        Create the required resource file for this FORUM_TOPIC block for the Common Cartridge export.
        """
        # TODO : Implement
        return False

    def _create_sit_block_resource_file(self,
                                        module_node: CourseNode,  # noqa: F841
                                        unit_block: UnitBlock,  # noqa: F841
                                        zip_file: ZipFile) -> bool:  # noqa: F841
        """
        Create the required resource file for this ASSESSMENT block for the Common Cartridge export.
        """
        # TODO : Implement
        return False

    def _create_assessment_block_resource_file(self,
                                               module_node: CourseNode,         # noqa: F841
                                               unit_block: UnitBlock,           # noqa: F841
                                               zip_file: ZipFile) -> bool:      # noqa: F841
        """
        Create the required resource file for this ASSESSMENT block for the Common Cartridge export.
        """
        # TODO : Implement
        return False

    def _block_resource_file_path(self, unit_block: UnitBlock) -> str:
        """
        Return the file name to use to export the given unit block.
        """
        block = unit_block.block

        folder_name = str(block.uuid)

        if block.display_name:
            filename = slugify(block.display_name) + ".html"
        else:
            filename = f"{block.type}.html"

        return folder_name + "/" + filename

    def _block_related_resource_file_path(self, block_resource: BlockResource) -> Optional[str]:
        """
        Return the file name to use to export the given block resource file.
        """
        block = block_resource.block

        folder_name = f"{self.WEB_RESOURCES_DIR}{block.uuid}"

        resource_file = block_resource.resource.resource_file

        if resource_file:
            filename = resource_file.name.split("/")[-1]
            return folder_name + "/" + filename

        return None

    def _create_html_block_resource_file(self,
                                         module_node: CourseNode,  # noqa: F841
                                         unit_block: UnitBlock,
                                         zip_file: ZipFile) -> bool:
        """
        Create the required resource file for this HTML_CONTENT block for the Common Cartridge export.
        """

        block = unit_block.block

        html_title = block.display_name if block.display_name else block.type

        html_content = self._html_content_with_relative_resource_file_paths(unit_block)

        html = f"""
<html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="identifier" content="{block.uuid}" />
    <meta name="editing_roles" content="teachers" />
    <meta name="workflow_state" content="active" />
    <title>{html_title}</title>
    </head>
    <body>
    {html_content}
    </body>
</html>
"""

        block_filename = self._block_resource_file_path(unit_block)
        zip_file.writestr(block_filename, html)

        return True

    def _create_video_block_resource_file(self,
                                          module_node: CourseNode,  # noqa: F841
                                          unit_block: UnitBlock,
                                          zip_file: ZipFile) -> bool:

        block = unit_block.block
        html = f"""
<html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="identifier" content="{block.uuid}" />
    <meta name="editing_roles" content="teachers" />
    <meta name="workflow_state" content="active" />
    <title>{block.display_name}</title>
    </head>
    <body>
       <iframe id="ytplayer{block.id}"
            type="text/html"
            width="640"
            height="360"
            src="https://www.youtube.com/embed/{block.video_id}"></iframe>
    </body>
</html>
"""

        block_filename = self._block_resource_file_path(unit_block)
        zip_file.writestr(block_filename, html)

        return True

    def _create_block_related_file(self, block_resource: BlockResource, zip_file: ZipFile) -> bool:
        """
        Create the required resource file for this BlockResource in the Common Cartridge export.
        """
        if not block_resource.resource.resource_file:
            return False

        export_file_path = self._block_related_resource_file_path(block_resource)
        resource_content = block_resource.resource.resource_file.path
        zip_file.write(resource_content, export_file_path)

        return True

    def _html_content_with_relative_resource_file_paths(self, unit_block: UnitBlock) -> str:
        """
        Returns the unit_block.block.html_content with any references to BlockResources updated to use their relative
        path in the Common Cartridge export.
        """
        html_content = unit_block.block.html_content

        for block_resource in unit_block.block.block_resources.all():

            resource_file = block_resource.resource.resource_file
            if not resource_file:
                continue

            # Convert the exported web resource path to an CC-relative path
            export_file_path = self._block_related_resource_file_path(block_resource)
            export_file_path = re.sub(self.WEB_RESOURCES_DIR, self.IMS_CC_ROOT_DIR, export_file_path)

            # Replace all occurances of the resource URL with its CC-relative, exported path.
            resource_file_name = settings.MEDIA_URL + resource_file.name
            resource_match = rf'["\']{resource_file_name}["\']'
            resource_replace = f'"{export_file_path}"'

            html_content = re.sub(resource_match, resource_replace, html_content)

        return html_content

    def _setup_namespaces_and_prefixes(self):
        # Set up namespaces and prefixes
        self.namespaces = {
            "": "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1",
            "lom": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/resource",
            "lomimscc": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/manifest",
            "cpx": "http://www.imsglobal.org/xsd/imsccv1p3/imscp_extensionv1p2",
        }
        # Register all namespace prefixes
        for prefix, uri in self.namespaces.items():
            if prefix:
                register_namespace(prefix, uri)

    def _create_manifest(self, course: Course) -> Element:
        """
        Create the manifest element for the Common Cartridge export.
        """

        manifest_el: Element = self._create_manifest_root_element(course=course)

        metadata_el: Element = self._create_metadata_xml(course=course)
        manifest_el.append(metadata_el)

        resources_el: Element = self._create_resources(course=course)
        manifest_el.append(resources_el)

        organizations_el: Element = self._create_organizations_xml(course=course)
        manifest_el.append(organizations_el)

        return manifest_el

    def _create_manifest_root_element(self, course) -> Element:
        """
        Create the root <manifest/> element for the Common Cartridge export.
        We need to add a bunch of namespaces to the root element.

        Returns:
            The <manifest/> element for the course, complete with namespaces.

        TODO:
            - Note entirely confident about when to use which namespaces. Refactor.
        """
        # SETUP ROOT ELEMENT
        # Define xsi:schemaLocation value
        schema_location = (
            "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/resource http://www.imsglobal.org/profile/cc/ccv1p3/LOM/ccv1p3_lomresource_v1p0.xsd "
            "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1 http://www.imsglobal.org/profile/cc/ccv1p3/ccv1p3_imscp_v1p2_v1p0.xsd "
            "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/manifest http://www.imsglobal.org/profile/cc/ccv1p3/LOM/ccv1p3_lommanifest_v1p0.xsd "
            "http://www.imsglobal.org/xsd/imsccv1p3/imscp_extensionv1p2 http://www.imsglobal.org/profile/cc/ccv1p3/ccv1p3_cpextensionv1p2_v1p0.xsd")

        manifest_el: Element = Element("manifest", attrib={
            "identifier": course.token,
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": schema_location,
        })
        # Add namespaces to the root element
        for prefix, uri in self.namespaces.items():
            if prefix:
                manifest_el.set(f"xmlns:{prefix}", uri)
            else:
                manifest_el.set("xmlns", uri)
        return manifest_el

    def _create_metadata_xml(self, course: Course) -> Element:
        """
        Create the metadata element for the Common Cartridge export.
        Populate with metadata about the course.

        Returns:
            The <metadata/> element for the course, complete with nested
            <lomimscc:lom> element.
        """

        metadata_el = Element("metadata")

        schema_el = Element("schema")
        schema_el.text = "IMS Common Cartridge"
        metadata_el.append(schema_el)

        schemaversion_el = Element("schemaversion")
        schemaversion_el.text = "1.3.0"
        metadata_el.append(schemaversion_el)

        lom_el = Element("lomimscc:lom")

        general_el = Element("lomimscc:general")
        title_el = Element("lomimscc:title")
        title_en_el = Element("lomimscc:string", attrib={"language": settings.LANGUAGE_CODE})
        title_en_el.text = course.display_name
        title_el.append(title_en_el)

        general_el.append(title_el)
        lom_el.append(general_el)

        lifecycle_el = Element("lomimscc:lifeCycle")
        contribute_el = Element("lomimscc:contribute")
        date_el = Element("lomimscc:date")
        dateTime_el = Element("lomimscc:dateTime")
        dateTime_el.text = course.created_at.strftime("%Y-%m-%d")
        date_el.append(dateTime_el)
        contribute_el.append(date_el)
        lifecycle_el.append(contribute_el)
        lom_el.append(lifecycle_el)
        rights_el = self._get_rights_el(course=course)
        lom_el.append(rights_el)

        metadata_el.append(lom_el)

        return metadata_el

    def _get_rights_el(self, course) -> Element:
        """
        Create the <rights/> element for the Common Cartridge export.

        Returns:
            The <lomimscc:rights/> element for the course, complete with nested
            <lomimscc:copyrightAndOtherRestrictions/>
            and <lomimscc:description/> elements.
        """

        rights_el = Element("lomimscc:rights")
        copyrightAndOtherRestrictions_el = Element("lomimscc:copyrightAndOtherRestrictions")
        value_el = Element("lomimscc:value")
        value_el.text = "yes"
        copyrightAndOtherRestrictions_el.append(value_el)
        rights_el.append(copyrightAndOtherRestrictions_el)

        if course.content_license:
            description_el = Element("lomimscc:description")
            description_str = f"{course.content_license} - https://creativecommons.org/licenses/by-nc-nd/4.0/"
            description_text = Element("lomimscc:string")
            description_text.text = description_str
            description_el.append(description_text)
            rights_el.append(description_el)

        return rights_el

    def _create_organizations_xml(self, course: Course) -> Element:
        """
        Create the required <organizations/> element for the Common Cartridge export.

        Not sure when we'll ever need more than one <organization/> for a CC export,
        but it is supported by standard.

        Returns:
            The <organizations/> element for the course, complete
            with an <organization/> element with nested structure of
            <item/> elements.

        """

        organizations_el = Element("organizations")
        organization_el = Element("organization",
                                  attrib={
                                      "identifier": "org_1",
                                      "structure": "rooted-hierarchy"
                                  })
        organizations_el.append(organization_el)
        item_el = self._create_organization_items(course=course)
        organization_el.append(item_el)

        return organizations_el

    def _create_organization_items(self, course: Course) -> Element:
        """
        Create the nested <item/> elements for the current course.

        Note that KinesinLMS supports a three-tier structure:
        Modules, Sections, and Units. However, Canvas only
        has modules to group individual items. So we will
        flatten the structure to have only modules and
        within that, an <item> for each block in each unit
        in each section of the module.

        Returns:
            The root <item/> element for the course content.

        """

        # According to the spec, an organization must have only one
        # <item> element as a child. This is the root of the hierarchy.
        rool_item_el: Element = Element("item")
        rool_item_el.attrib["identifier"] = "LearningModules"

        for m_idx, module_node in enumerate(course.course_root_node.get_children()):
            module_id_ref = f"module_{m_idx}"
            module_el: Element = Element("item", attrib={"identifier": module_id_ref})
            module_title_el: Element = Element("title")
            if module_node.display_name:
                module_title_el.text = module_node.display_name
            else:
                module_title_el.text = "Module {m_idx}"
            module_el.append(module_title_el)

            rool_item_el.append(module_el)

            for s_idx, section_node in enumerate(module_node.get_children()):

                section_id_ref = f"section_{m_idx}_{s_idx}"
                section_el: Element = Element("item", attrib={"identifier": section_id_ref})
                section_title_el: Element = Element("title")
                if section_node.display_name:
                    section_title_el.text = section_node.display_name
                else:
                    section_title_el.text = f"Section {m_idx}"
                section_el.append(section_title_el)

                module_el.append(section_el)

                for u_idx, unit_node in enumerate(section_node.get_children()):

                    unit_title = unit_node.display_name or f"Unit {u_idx}"

                    for unit_block in unit_node.unit.unit_blocks.all():
                        block = unit_block.block

                        block_id_ref = f"block_{block.uuid}"
                        block_el = Element("item", attrib={"identifier": block_id_ref, "identifierref": str(block.uuid)})
                        section_el.append(block_el)

                        block_title = block.display_name or block.type
                        title_el: Element = Element("title")
                        title_el.text = f"{unit_title} : {block_title}"
                        block_el.append(title_el)

        return rool_item_el

    def _create_resources(self, course) -> Element:
        """
        Create the required <resources/> element for the Common Cartridge export.

        Returns:
            The <resources/> element for the course, complete with nested
            <resource/> elements for each resource used in the course.

        """
        resources_el = Element("resources")
        for module_node in course.course_root_node.get_children():
            for section_node in module_node.get_children():
                for unit_node in section_node.get_children():
                    for unit_block in unit_node.unit.unit_blocks.all():
                        resource_el = self._create_block_resource(module_node=module_node,
                                                                  unit_block=unit_block)
                        resources_el.append(resource_el)

                        for block_resource in unit_block.block.block_resources.all():
                            related_resource_el = self._create_block_related_resource(block_resource)
                            if related_resource_el:
                                resources_el.append(related_resource_el)

        return resources_el

    def _create_block_resource(self, module_node: CourseNode, unit_block: UnitBlock) -> Element:   # noqa: F841
        """
        Create the required <resource/> element for the Common Cartridge export.
        """

        # Create <resource/> element
        block = unit_block.block
        resource_el = Element("resource", attrib={
            "identifier": str(block.uuid),
            "type": "webcontent",
        })

        if block.type in [BlockType.HTML_CONTENT.name, BlockType.VIDEO.name]:
            # Create nested <file/> element
            file_href = self._block_resource_file_path(unit_block)
            file_el = Element("file", attrib={"href": file_href})
            resource_el.append(file_el)

        return resource_el

    def _create_block_related_resource(self, block_resource: BlockResource) -> Optional[Element]:
        """
        Create the required <resource/> element for the Common Cartridge export.
        """

        # Create <resource/> element
        resource_file_path = self._block_related_resource_file_path(block_resource)
        if not resource_file_path:
            return None

        resource = block_resource.resource
        resource_el = Element("resource", attrib={
            "identifier": str(resource.uuid),
            "type": "webcontent",
            "href": resource_file_path,
        })

        # Create nested <file/> element
        file_el = Element("file", attrib={"href": resource_file_path})
        resource_el.append(file_el)

        return resource_el
