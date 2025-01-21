import json
import logging
import os
import shutil
import tempfile
from io import BytesIO
from zipfile import ZipFile

from django.conf import settings

from kinesinlms.composer.import_export.exporter import BaseExporter
from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)


class OpenEdXExporter(BaseExporter):
    """
    Exports a course to Open edX format.
    The export includes JSON descriptors and content resources, packaged as a zip file.
    """

    def __init__(self):
        pass

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def export_course(self, course: Course, export_format: str) -> BytesIO:
        """
        Build and return an Open edX export of the given course.
        An Open edX export is a zip file containing:
            -   course directory structure with JSON descriptor files
            -   content resources (HTML, images, etc.)

        Args:
            course (Course): The course to export
            export_format (str): The export format, e.g., 'open_edx'

        Raises:
            ValueError: if arguments are invalid
            Exception: if an error occurs during export

        Returns:
            BytesIO: A BytesIO object containing the Open edX export.
                     This is effectively a zip file.
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
            # Step 1: Create course directory structure
            course_dir = os.path.join(temp_dir, course.token)
            os.makedirs(course_dir, exist_ok=True)
            logger.debug(f"Created course directory at {course_dir}")

            # Step 2: Generate course.json
            self._create_course_json(course, course_dir)

            # Step 3: Generate sections.json, units.json, components.json
            self._create_course_structure_json(course, course_dir)

            # Step 4: Collect and copy content resources
            self._collect_content_resources(course, course_dir)

            # Step 5: Package the course directory into a zip file
            bytes_io = BytesIO()
            with ZipFile(bytes_io, "w") as zf:
                for root, dirs, files in os.walk(course_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Compute the archive name by removing the temp_dir prefix
                        archive_name = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arcname=archive_name)
                        logger.debug(f"Added '{file_path}' as '{archive_name}' to zip.")

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
        export_filename = "{}_{}_export.zip".format(course.slug, course.run)
        return export_filename

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _create_course_json(self, course: Course, course_dir: str):
        """
        Create the course.json descriptor file for Open edX.

        Args:
            course (Course): The course to export
            course_dir (str): Path to the course directory
        """
        course_json_path = os.path.join(course_dir, "course.json")
        course_data = {
            "course": {
                "display_name": course.display_name or "Untitled Course",
                "overview": course.overview or "",
                "language": settings.LANGUAGE_CODE,
                "start": course.start_date.isoformat() if course.start_date else "",
                "end": course.end_date.isoformat() if course.end_date else "",
                "metadata": {
                    "tags": [tag.name for tag in course.tags.all()],
                    "license": course.content_license or "No license defined",
                },
                "structure": {
                    "sections": [],  # To be filled in by _create_course_structure_json
                },
            }
        }

        with open(course_json_path, "w", encoding="utf-8") as f:
            json.dump(course_data, f, indent=4)
            logger.debug(f"Created course.json at {course_json_path}")

    def _create_course_structure_json(self, course: Course, course_dir: str):
        """
        Create the sections.json, units.json, and components.json descriptor files.

        Args:
            course (Course): The course to export
            course_dir (str): Path to the course directory
        """
        sections = []
        units = []
        components = []

        # Traverse the course hierarchy: Modules -> Sections -> Units -> Components
        for m_idx, module_node in enumerate(course.course_root_node.get_children(), start=1):
            section_id = f"section_{module_node.id}"
            section = {
                "id": section_id,
                "display_name": module_node.display_name or f"Module {m_idx}",
                "units": [],
            }
            logger.debug(f"Processing Module: {module_node.display_name or f'Module {m_idx}'}")

            for s_idx, section_node in enumerate(module_node.get_children(), start=1):
                unit_id = f"unit_{section_node.id}"
                unit = {
                    "id": unit_id,
                    "display_name": section_node.display_name or f"Section {s_idx}",
                    "components": [],
                }
                logger.debug(f"  Processing Section: {section_node.display_name or f'Section {s_idx}'}")

                for u_idx, unit_node in enumerate(section_node.get_children(), start=1):
                    component_id = f"component_{unit_node.id}"
                    component = {
                        "id": component_id,
                        "display_name": unit_node.display_name or f"Unit {u_idx}",
                        "type": "html",  # Adjust based on block type
                        "source": f"components/{component_id}.json",
                    }
                    unit["components"].append(component)
                    components.append(self._create_component_json(unit_node, course_dir, component_id))
                    logger.debug(f"    Added Component: {unit_node.display_name or f'Unit {u_idx}'}")

                section["units"].append(unit)
                units.append(unit)

            sections.append(section)

        # Write sections.json
        sections_json_path = os.path.join(course_dir, "sections.json")
        with open(sections_json_path, "w", encoding="utf-8") as f:
            json.dump({"sections": sections}, f, indent=4)
            logger.debug(f"Created sections.json at {sections_json_path}")

        # Write units.json
        units_json_path = os.path.join(course_dir, "units.json")
        with open(units_json_path, "w", encoding="utf-8") as f:
            json.dump({"units": units}, f, indent=4)
            logger.debug(f"Created units.json at {units_json_path}")

        # Write components.json
        components_json_path = os.path.join(course_dir, "components.json")
        with open(components_json_path, "w", encoding="utf-8") as f:
            json.dump({"components": components}, f, indent=4)
            logger.debug(f"Created components.json at {components_json_path}")

    def _create_component_json(self, unit_node, course_dir: str, component_id: str) -> dict:
        """
        Create the JSON descriptor for an individual component (XBlock).

        Args:
            unit_node: The unit node containing the block
            course_dir (str): Path to the course directory
            component_id (str): Unique identifier for the component

        Returns:
            dict: The component's JSON descriptor
        """
        block = unit_node.unit.unit_blocks.first().block  # Assuming one block per unit
        component_type = self._map_block_type_to_xblock(block.type)
        component_source_path = os.path.join(course_dir, "components")

        os.makedirs(component_source_path, exist_ok=True)

        component_data = {
            "id": component_id,
            "type": component_type,
            "fields": {
                "display_name": block.display_name or "Untitled Component",
                "html_content": self._get_block_content(block),
            },
        }

        component_json_path = os.path.join(component_source_path, f"{component_id}.json")
        with open(component_json_path, "w", encoding="utf-8") as f:
            json.dump(component_data, f, indent=4)
            logger.debug(f"Created component JSON at {component_json_path}")

        return component_data

    def _map_block_type_to_xblock(self, block_type: str) -> str:
        """
        Map KinesinLMS block types to Open edX XBlock types.

        Args:
            block_type (str): The type of the block in KinesinLMS

        Returns:
            str: Corresponding XBlock type for Open edX
        """
        mapping = {
            "html": "html",
            "video": "video",
            "problem": "problem",
            # Add more mappings as needed
        }
        return mapping.get(block_type, "html")  # Default to 'html' if unknown

    def _get_block_content(self, block: Block) -> str:
        """
        Retrieve the HTML or relevant content from a block.

        Args:
            block (Block): The block instance

        Returns:
            str: HTML content or other content as a string
        """
        if block.type == "html":
            return block.content_html or ""
        elif block.type == "video":
            return block.content_video_url or ""
        elif block.type == "problem":
            return block.content_problem_json or ""
        else:
            return ""

    def _collect_content_resources(self, course: Course, course_dir: str):
        """
        Collect and copy all necessary content resources into the course directory.

        Args:
            course (Course): The course to export
            course_dir (str): Path to the course directory
        """
        resources_dir = os.path.join(course_dir, "resources")
        os.makedirs(resources_dir, exist_ok=True)
        logger.debug(f"Created resources directory at {resources_dir}")

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
