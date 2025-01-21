import logging
import os
import shutil
import tarfile
import tempfile
from io import BytesIO

from django.conf import settings
from lxml import etree

from kinesinlms.composer.import_export.exporter import BaseExporter
from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)


class OpenEdXExporter(BaseExporter):
    """
    Exports a course to Open edX Open Learning XML format.
    The export includes XML descriptor files and content resources, packaged as a tar.gz file.
    """

    def __init__(self):
        # Initialize any required attributes
        pass

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def export_course(self, course: Course, export_format: str) -> BytesIO:
        """
        Build and return an Open edX Open Learning XML export of the given course.
        An Open edX export is a tar.gz file containing:
            -   course.xml file
            -   Components directory with content XML files
            -   Resources directory with media files

        Args:
            course (Course): The course to export
            export_format (str): The export format, should be 'open_edx'

        Raises:
            ValueError: if arguments are invalid
            Exception: if an error occurs during export

        Returns:
            BytesIO: A BytesIO object containing the Open edX export.
                     This is effectively a tar.gz file.
        """

        if not course:
            raise ValueError("Course must be specified for export.")
        if export_format.lower() != "open_edx":
            raise ValueError(f"Export format '{export_format}' not supported.")

        logger.info(f"Starting Open edX export for course: {course.display_name}")

        # Create a temporary directory to assemble the course structure
        temp_dir = tempfile.mkdtemp()
        logger.debug(f"Created temporary directory at {temp_dir}")

        try:
            # Step 1: Create course.xml
            course_xml_path = os.path.join(temp_dir, "course.xml")
            self._create_course_xml(course, course_xml_path)

            # Step 2: Create Components directory and component XML files
            components_dir = os.path.join(temp_dir, "components")
            os.makedirs(components_dir, exist_ok=True)
            logger.debug(f"Created components directory at {components_dir}")
            self._create_components_xml(course, components_dir)

            # Step 3: Collect and copy content resources
            resources_dir = os.path.join(temp_dir, "resources")
            os.makedirs(resources_dir, exist_ok=True)
            logger.debug(f"Created resources directory at {resources_dir}")
            self._collect_content_resources(course, resources_dir)

            # Step 4: Package the course directory into a tar.gz file
            bytes_io = BytesIO()
            with tarfile.open(fileobj=bytes_io, mode="w:gz") as tar:
                tar.add(course_xml_path, arcname="course.xml")
                tar.add(components_dir, arcname="components")
                tar.add(resources_dir, arcname="resources")
                logger.debug("Added course.xml, components/, and resources/ to tar.gz")

            bytes_io.seek(0)
            logger.info(f"Successfully created Open edX export for course: {course.display_name}")

            return bytes_io

        except Exception as e:
            logger.exception(f"Error exporting course '{course.display_name}' to Open edX format: {e}")
            raise e

        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
            logger.debug(f"Deleted temporary directory at {temp_dir}")

    def get_export_filename(self, course: Course) -> str:
        export_filename = "{}_{}_export.tar.gz".format(course.slug, course.run)
        return export_filename

    def get_content_type(self) -> str:
        # Open EdX exports as tar.gz
        return "application/gzip"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _create_course_xml(self, course: Course, course_xml_path: str):
        """
        Create the course.xml descriptor file for Open edX.

        Args:
            course (Course): The course to export
            course_xml_path (str): Path to save course.xml
        """
        logger.debug(f"Creating course.xml at {course_xml_path}")

        # Define namespaces if any, for Open edX XML schema
        NSMAP = {
            None: "http://www.edx.org/open-learning-xml",  # Default namespace
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

        # Create root element
        course_el = etree.Element("course", nsmap=NSMAP)
        course_el.set("title", course.display_name or "Untitled Course")
        course_el.set("description", course.overview or "")
        course_el.set("language", settings.LANGUAGE_CODE)

        # Add metadata if necessary
        metadata_el = etree.SubElement(course_el, "metadata")
        metadata_el.set("license", course.content_license or "No license defined")
        metadata_el.set("tags", ",".join([tag.name for tag in course.tags.all()]))

        # Add course structure
        structure_el = etree.SubElement(course_el, "structure")
        for module_node in course.course_root_node.get_children():
            section_el = etree.SubElement(structure_el, "section")
            section_el.set("title", module_node.display_name or "Untitled Module")
            for section_node in module_node.get_children():
                unit_el = etree.SubElement(section_el, "unit")
                unit_el.set("title", section_node.display_name or "Untitled Section")
                for unit_node in section_node.get_children():
                    component_ref = etree.SubElement(unit_el, "component_ref")
                    component_ref.set("ref", f"components/component_{unit_node.id}.xml")

        # Serialize XML to file
        tree = etree.ElementTree(course_el)
        tree.write(course_xml_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
        logger.debug("course.xml created successfully.")

    def _create_components_xml(self, course: Course, components_dir: str):
        """
        Create individual component XML files for each block in the course.

        Args:
            course (Course): The course to export
            components_dir (str): Directory to save component XML files
        """
        logger.debug(f"Creating component XML files in {components_dir}")

        for module_node in course.course_root_node.get_children():
            for section_node in module_node.get_children():
                for unit_node in section_node.get_children():
                    for unit_block in unit_node.unit.unit_blocks.all():
                        block = unit_block.block
                        component_id = f"component_{block.id}"
                        component_xml_path = os.path.join(components_dir, f"{component_id}.xml")
                        self._create_component_xml(block, component_xml_path)
                        logger.debug(f"Created component XML for block ID {block.id} at {component_xml_path}")

    def _create_component_xml(self, block: Block, component_xml_path: str):
        """
        Create an individual component XML file based on the block type.

        Args:
            block (Block): The block instance
            component_xml_path (str): Path to save the component XML
        """
        logger.debug(f"Creating component XML for block ID {block.id} at {component_xml_path}")

        # Define namespaces if any
        NSMAP = {
            None: "http://www.edx.org/open-learning-xml",  # Default namespace
        }

        # Create root element based on block type
        component_type = self._map_block_type_to_xblock(block.type)
        component_el = etree.Element(component_type, nsmap=NSMAP)

        # Common fields
        component_el.set("title", block.display_name or "Untitled Component")
        component_el.set("id", f"component_{block.id}")

        # Add content based on block type
        if block.type == "html":
            content_el = etree.SubElement(component_el, "content")
            content_el.text = block.html_content or ""
        elif block.type == "video":
            video_el = etree.SubElement(component_el, "video")
            video_el.set("url", block.content_video_url or "")
            video_el.set("caption", block.content_video_caption or "")
        elif block.type == "problem":
            problem_el = etree.SubElement(component_el, "problem")
            problem_el.set("source", block.content_problem_json or "")
        else:
            # Default to HTML content if type is unknown
            content_el = etree.SubElement(component_el, "content")
            content_el.text = block.html_content or ""

        # Serialize XML to file
        tree = etree.ElementTree(component_el)
        tree.write(component_xml_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
        logger.debug(f"Component XML for block ID {block.id} created successfully.")

    def _map_block_type_to_xblock(self, block_type: str) -> str:
        """
        Map KinesinLMS block types to Open edX component XML types.

        Args:
            block_type (str): The type of the block in KinesinLMS

        Returns:
            str: Corresponding component XML type for Open edX
        """
        mapping = {
            "html": "html_component",
            "video": "video_component",
            "problem": "problem_component",
            # Add more mappings as needed
        }
        return mapping.get(block_type, "html_component")  # Default to 'html_component' if unknown

    def _collect_content_resources(self, course: Course, resources_dir: str):
        """
        Collect and copy all necessary content resources into the resources directory.

        Args:
            course (Course): The course to export
            resources_dir (str): Path to the resources directory
        """
        logger.debug(f"Collecting content resources into {resources_dir}")

        # Iterate through all blocks and copy their resources
        for module_node in course.course_root_node.get_children():
            for section_node in module_node.get_children():
                for unit_node in section_node.get_children():
                    for unit_block in unit_node.unit.unit_blocks.all():
                        block = unit_block.block
                        resource_files = self._get_block_resources(block)
                        for resource in resource_files:
                            self._copy_resource_file(resource, resources_dir)

    def _get_block_resources(self, block: Block) -> list:
        """
        Retrieve a list of resource file paths associated with a block.

        Args:
            block (Block): The block instance

        Returns:
            list: List of file paths
        """
        resources = []
        for block_resource in block.block_resources.all():
            resource_path = block_resource.resource.file.path  # Adjust based on your model
            resources.append(resource_path)
        return resources

    def _copy_resource_file(self, source_path: str, dest_dir: str):
        """
        Copy a resource file from source to destination directory.

        Args:
            source_path (str): Path to the source file
            dest_dir (str): Destination directory path
        """
        try:
            if os.path.exists(source_path):
                shutil.copy(source_path, dest_dir)
                logger.debug(f"Copied resource '{source_path}' to '{dest_dir}'")
            else:
                logger.warning(f"Resource file '{source_path}' does not exist and will be skipped.")
        except Exception as e:
            logger.error(f"Error copying resource '{source_path}': {e}")
            raise e
