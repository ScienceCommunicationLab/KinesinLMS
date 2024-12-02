# NOTE: There's some terminology confusion here. The term "resource" is used
# in two different ways. In the context of the Common Cartridge export, a
# "resource" is a file that is part of the export (could be html, etc).
#
# In the context of the Learning Library, a "resource" is a model that
# represents a file that is linked to a Block via BlockResource.

import logging
import re
from abc import ABC, abstractmethod
from typing import Optional
from zipfile import ZipFile

from django.conf import settings
from lxml import etree
from slugify import slugify

from kinesinlms.composer.import_export.common_cartridge.assessment import QTIAssessmentFactory
from kinesinlms.composer.import_export.common_cartridge.constants import (
    CommonCartridgeExportDir,
    CommonCartridgeResourceType,
)
from kinesinlms.composer.import_export.common_cartridge.utils import validate_resource_path
from kinesinlms.course.models import CourseNode, UnitBlock
from kinesinlms.learning_library.constants import ResourceType
from kinesinlms.learning_library.models import (
    BlockResource,
    BlockType,
)

logger = logging.getLogger(__name__)


class CCHandler(ABC):
    """
    Base class for creating a common cartridge resource.
    Our factory will use a child class to create a resource
    for a particular kind of Block.

    Args:
        ABC (_type_): _description_
    """

    unit_block: UnitBlock = None

    def __init__(self, unit_block: UnitBlock):
        if not unit_block:
            raise ValueError("unit_block must be provided")
        self.unit_block = unit_block

    @property
    def block_type(self) -> Optional[str]:
        if self.unit_block:
            return self.unit_block.block.type
        return None

    @abstractmethod
    def get_cc_resource_type(self):
        pass

    # METHODS FOR CREATING ELEMENTS FOR CC XML
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def create_cc_resource_element_for_unit_block(self) -> etree.Element:
        """
        Create the <resource> element for this UnitBlock instance.
        This element will be added to the <resources> element in the
        <manifest/> element in the Common Cartridge export.

        Something like this:

                <resources>
                    <!-- HTML Content Resource -->
                    <resource identifier="html_123" type="webcontent" href="html_123/content.html">
                        <file href="html_123/content.html"/>
                    </resource>

                    <!-- Video Resource -->
                    <resource identifier="video_456" type="imswl_xmlv1p3" href="video_456/video.html">
                        <file href="video_456/video.html"/>
                    </resource>
                </resources>

        Args:
            unit_block (UnitBlock): _description_

        Returns:
            etree.Element: _description_
        """
        if not self.unit_block:
            raise ValueError("unit_block must be already provided")

        # Create <resource/> element
        resource_type = self.get_cc_resource_type()
        resource_el = etree.Element(
            "resource",
            attrib={
                "identifier": self.unit_block.id_for_cc,
                "type": resource_type,
            },
        )

        # Create nested <file/> element, in needed
        file_el = self._get_file_element(self.unit_block)
        if file_el is not None:
            resource_el.append(file_el)

        return resource_el

    def create_cc_resource_element_for_block_related_resource(
        self,
        block_resource: BlockResource,
    ) -> Optional[etree.Element]:
        """
        Create the required <resource/> element for Resources instances related
        to the current block via BlockResource.
        """

        # Get the file path for the resource so we can add it to <resource/>
        resource_file_path = self._block_related_resource_file_path(
            block_resource=block_resource,
        )
        if not resource_file_path:
            return None

        # Create <resource/> element
        resource = block_resource.resource
        if resource.type == ResourceType.IMAGE.name:
            resource_type = CommonCartridgeResourceType.WEB_CONTENT.value
        elif resource.type == ResourceType.VIDEO_TRANSCRIPT.name:
            resource_type = CommonCartridgeResourceType.ASSIGNMENT.value

        resource_el = etree.Element(
            "resource",
            attrib={
                "identifier": str(resource.uuid),
                "type": resource_type,
                "href": resource_file_path,
            },
        )

        # Create nested <file/> element
        file_el = etree.Element("file", attrib={"href": resource_file_path})
        resource_el.append(file_el)

        return resource_el

    # METHODS FOR CREATING FILES TO BE ADDED TO CC ZIP
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ):
        """
        This method should create a "resource" file within the zip for a particular
        type of block.

        Args:
            module_node (CourseNode): The module node that contains the block.
            unit_block (UnitBlock): The unit block that contains the block.
            zip_file (ZipFile): The zip file to which the resource file should be added.

        Returns:
            bool:   True if the resource file was created and added successfully.
                    (otherwise an Exception should be raised)
        """
        pass

    def create_cc_file_for_block_related_resource(
        self,
        block_resource: BlockResource,
        zip_file: ZipFile,
    ) -> bool:
        """
        Create the required Common Cartridge resource file for the Resource
        item linked by the incoming BlockResource.

        Args:
            block_resource (BlockResource): The BlockResource instance to export.
            zip_file (ZipFile): The zip file to which the resource file should be added.

        Returns:
            bool:   True if the resource file was created and added successfully.


        """
        if not block_resource.resource or block_resource.resource.resource_file:
            return False

        resource_file = block_resource.resource.resource_file

        if not resource_file:
            return False

        resource_export_file_path = self._block_related_resource_file_path(
            block_resource=block_resource,
        )
        resource_content = block_resource.resource.resource_file

        zip_file.write(resource_content, resource_export_file_path)

        return True

    # ~~~~~~~~~~~~~~~~~~~~~~
    # Private methods
    # ~~~~~~~~~~~~~~~~~~~~~~

    def _get_file_element(self, unit_block: UnitBlock) -> Optional[etree.Element]:
        """
        Create a <file> element for the resource file associated with the given UnitBlock.

        It will look like this:

              <file href="some-uuid/HTML_CONTENT.html"/>

        Args:
            unit_block (UnitBlock): The unit block that contains the block.

        Returns:
            Optional[etree.Element]: The <file> element, or None if no file element is needed.

        """
        if not unit_block:
            raise ValueError("unit_block must be provided")

        resource_file_path = self._block_resource_file_path()
        if not resource_file_path:
            return None
        file_el = etree.Element("file", attrib={"href": resource_file_path})
        return file_el

    def _reformat_html_content_with_relative_resource_file_paths(
        self,
        unit_block: UnitBlock,
    ) -> str:
        """
        Returns the unit_block.block.html_content with any references to BlockResources
        updated to use their relative path in the Common Cartridge export.

        So essentially what we're doing is replacing template tags in the HTML content
        like "{{ block_resource_url 'filename.jpg' }}" with the relative path to the
        exported file for that Resource as saved into the Common Cartridge export.

        """
        html_content = unit_block.block.html_content

        for block_resource in unit_block.block.block_resources.all():
            resource_file = block_resource.resource.resource_file
            if not resource_file:
                continue

            # Get the base filename without path
            filename = resource_file.name.split("/")[-1]

            # Convert the exported web resource path to a CC-relative path
            export_file_path = self._block_related_resource_file_path(block_resource=block_resource)
            export_file_path = re.sub(
                CommonCartridgeExportDir.WEB_RESOURCES_DIR.value,
                CommonCartridgeExportDir.IMS_CC_ROOT_DIR.value,
                export_file_path,
            )

            # Replace Django template tags using the filename
            exp = r'{{\%\s*block_resource_url\s+[\'"]{}[\'"]\s*\%}}'
            template_tag_pattern = exp.format(filename)

            # Add debug logging
            logger.debug(f"Looking for template tag pattern: {template_tag_pattern}")
            logger.debug(f"In content: {html_content}")
            logger.debug(f"Will replace with: {export_file_path}")

            html_content = re.sub(template_tag_pattern, export_file_path, html_content)

            # Also replace any direct media URLs
            resource_file_name = settings.MEDIA_URL + resource_file.name
            resource_match = rf'["\']({re.escape(resource_file_name)})["\']'
            resource_replace = f'"{export_file_path}"'
            html_content = re.sub(resource_match, resource_replace, html_content)

        return html_content

    def _block_resource_file_path(self) -> str:
        """
        Generate a path to use when exporting the given unit block.
        We use the block's UUID as the folder name, and the block's display name
        (if it has one) as the file name.
        """

        if not self.unit_block:
            raise ValueError("unit_block must be provided")

        block = self.unit_block.block

        folder_name = str(block.uuid)

        if block.display_name:
            filename = slugify(block.display_name) + ".html"
        else:
            filename = f"{block.type}.html"

        path = folder_name + "/" + filename

        if not validate_resource_path(path):
            raise ValueError(f"Invalid resource path generated: {path}")

        return path

    def _block_related_resource_file_path(
        self,
        block_resource: BlockResource,
    ) -> str:
        """
        Generate a path to use when exporting the given Resource instance
        used by the provided BlockResource.

        We use the resource's UUID as the folder name, and the resource's
        file name as the file name.

        Args:
            block_resource (BlockResource): _description_

        Returns:
            str: _description_
        """
        uuid = str(block_resource.resource.uuid)
        folder_name = f"{CommonCartridgeExportDir.WEB_RESOURCES_DIR.value}{uuid}"
        resource = block_resource.resource
        filename = resource.resource_file.name.split("/")[-1]
        resource_export_file_path = folder_name + "/" + filename
        return resource_export_file_path


class HTMLContentCCResource(CCHandler):
    def get_cc_resource_type(self) -> str:
        return CommonCartridgeResourceType.WEB_CONTENT.value

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for a HTML_CONTENT type block.
        Adds the file to the zip file.
        """
        html_title = self.block.display_name if self.block.display_name else self.block.type
        html_content = self._reformat_html_content_with_relative_resource_file_paths(self.unit_block)
        html = f"""
<html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="identifier" content="{self.block.uuid}" />
    <meta name="editing_roles" content="teachers" />
    <meta name="workflow_state" content="active" />
    <title>{html_title}</title>
    </head>
    <body>
    {html_content}
    </body>
</html>
"""
        block_filename = self._block_resource_file_path()
        zip_file.writestr(block_filename, html)

        return True


class VideoCCResource(CCHandler):
    def get_cc_resource_type(self) -> str:
        # We store video as a simple HTML document with an embedded iframe.
        return CommonCartridgeResourceType.WEB_CONTENT.value

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for a VIDEO type block.
        Adds the file to the zip file.
        """
        html = f"""
<html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="identifier" content="{self.block.uuid}" />
    <meta name="editing_roles" content="teachers" />
    <meta name="workflow_state" content="active" />
    <title>{self.block.display_name}</title>
    </head>
    <body>
       <iframe id="ytplayer{self.block.id}"
            type="text/html"
            width="640"
            height="360"
            src="https://www.youtube.com/embed/{self.block.video_id}"></iframe>
    </body>
</html>
"""

        block_filename = self._block_resource_file_path()
        zip_file.writestr(block_filename, html)

        return True

    def get_manifest_entry(self, identifier: str, resource_path: str) -> str:
        return f"""
            <resource identifier="{identifier}" type="webcontent" href="{resource_path}">
                <file href="{resource_path}"/>
            </resource>
        """


class AssessmentCCResource(CCHandler):
    """
    Creates Common Cartridge resources for Assessment blocks.
    Uses a factory to generate the appropriate QTI content based on assessment type.
    """

    def __init__(self, unit_block: UnitBlock):
        super().__init__(unit_block=unit_block)
        self.qti_factory = QTIAssessmentFactory()

    def get_cc_resource_type(self) -> str:
        return CommonCartridgeResourceType.QTI_ASSESSMENT.value

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge QTI XML file for an assessment block.
        Uses the QTIAssessmentFactory to generate appropriate QTI content
        based on the assessment type.
        """
        if not hasattr(self.unit_block.block, "assessment"):
            raise ValueError("UnitBlock must have an assessment attribute")

        # Get QTI content from factory based on assessment type
        assessment = self.unit_block.block.assessment
        qti_assessment = self.qti_factory.create_qti_assessment(assessment)
        qti_xml = qti_assessment.to_qti_xml()

        # Write the QTI XML file to the zip
        assessment_file_path = self._block_resource_file_path()
        zip_file.writestr(assessment_file_path, qti_xml)
        return True

    def _block_resource_file_path(self) -> str:
        """
        Override the base class method to use .xml extension instead of .html
        """
        if not self.unit_block:
            raise ValueError("unit_block must be provided")
        block = self.unit_block.block
        folder_name = str(block.uuid)
        if block.display_name:
            filename = slugify(block.display_name) + ".xml"
        else:
            filename = f"{block.type}.xml"
        return folder_name + "/" + filename


class ForumTopicCCResource(CCHandler):
    def get_cc_resource_type(self) -> str:
        return CommonCartridgeResourceType.DISCUSSION_TOPIC.value

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for an FORUM_TOPIC type block.
        Adds the file to the zip file.
        """

        logger.warning(f"Forum topic block export not yet implemented: {self.block}")


class SimpleInteractiveToolCCResource(CCHandler):
    def get_cc_resource_type(self) -> str:
        return CommonCartridgeResourceType.LEARNING_RESOURCE.value

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for an SIMPLE_INTERACTIVE_TOOL type block.
        Adds the file to the zip file.
        """
        logger.warning(f"Assessment block export not yet implemented: {self.block}")


class JupyterNotebookCCResource(CCHandler):
    def get_cc_resource_type(self) -> str:
        return CommonCartridgeResourceType.LEARNING_RESOURCE.value

    def create_cc_file_for_unit_block(
        self,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for an JUPYTER_NOTEBOOK type block.
        Adds the file to the zip file.
        """
        logger.warning(f"Assessment block export not yet implemented: {self.block}")
