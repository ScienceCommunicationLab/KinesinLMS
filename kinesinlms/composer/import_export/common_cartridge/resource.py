# NOTE: There's some terminology confusion here. The term "resource" is used
# in two different ways. In the context of the Common Cartridge export, a
# "resource" is a file that is part of the export (could be html, etc).
#
# In the context of the Learning Library, a "resource" is a model that
# represents a file that is linked to a Block via BlockResource.

import logging
from abc import ABC, abstractmethod
from typing import Optional
from zipfile import ZipFile

from lxml import etree
from slugify import slugify

from kinesinlms.composer.import_export.common_cartridge.assessment import QTIAssessmentFactory
from kinesinlms.composer.import_export.common_cartridge.constants import (
    CommonCartridgeExportDir,
    CommonCartridgeResourceType,
)
from kinesinlms.composer.import_export.common_cartridge.utils import validate_resource_path
from kinesinlms.core.templatetags.core_tags import render_html_content
from kinesinlms.course.models import UnitBlock
from kinesinlms.learning_library.constants import ResourceType
from kinesinlms.learning_library.models import (
    BlockResource,
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
        self.block = unit_block.block

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
        # we store the resource file in the web_resources directory
        resource_file_path = f"{CommonCartridgeExportDir.WEB_RESOURCES_DIR.value}/{resource_file_path}"

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
        if not block_resource.resource or not block_resource.resource.resource_file:
            logger.warning(f"BlockResource {block_resource} has no resource file to export.")
            return False

        resource_file = block_resource.resource.resource_file
        resource_export_file_path = self._block_related_resource_file_path(
            block_resource=block_resource,
        )
        resource_export_file_path = f"{CommonCartridgeExportDir.WEB_RESOURCES_DIR.value}/{resource_export_file_path}"

        # Read the file content and write it to the zip
        with resource_file.open("rb") as f:
            zip_file.writestr(resource_export_file_path, f.read())

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
        like "{% block_resource_url 'filename.jpg' %}" with the relative path to the
        exported file for that Resource as saved into the Common Cartridge export.

        """

        html_content = unit_block.block.html_content
        if html_content is None:
            return ""

        for block_resource in unit_block.block.block_resources.all():
            resource_file = block_resource.resource.resource_file
            if not resource_file:
                continue

            # First, render the html_content so the path is updated from the template tag
            # to the full URL that would have been rendered.
            context = {
                "request": None,
                "block": unit_block.block,
            }
            html_content = render_html_content(context, item=unit_block.block)

            # Get the full URL that would have been rendered
            full_url = block_resource.resource.url

            # Get path that we're going to save this resource to in the CC...
            target_cc_path = self._block_related_resource_file_path(block_resource=block_resource)
            # Add funny prefix to make it a relative path
            target_cc_path = f"{CommonCartridgeExportDir.IMS_CC_ROOT_DIR.value}/{target_cc_path}"

            html_content = html_content.replace(full_url, target_cc_path)

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
        target_folder_name = uuid
        resource = block_resource.resource
        filename = resource.resource_file.name.split("/")[-1]
        resource_export_file_path = target_folder_name + "/" + filename
        return resource_export_file_path


class SurveyCCResource(CCHandler):
    """
    Export a SURVEY-type block to CC.
    For now that just means writing some HTML with the survey URL.

    Args:
        CCHandler (_type_): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """

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

        try:
            survey = self.block.survey_block.survey
        except Exception:
            logger.exception(f"Could not get survey for block {self.block}")
            return {}

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
    <div>
        <div>Course Survey</div>
        <div>{html_content}</div>
        <table>
            <tr>
                <td>Name:</td>
                <td>{survey.name}</td>
            </tr>
            <tr>
            <td>URL:</td>
                <td>
                    <a href="{survey.url}">{survey.url}</a>
                </td>
            </tr>
        </table>
    </body>
</html>
"""
        block_filename = self._block_resource_file_path()
        zip_file.writestr(block_filename, html)

        return True


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

    The XML generation is handled by the QTI assessment classes themselves, which include:
    - Standard XML namespaces via get_xml_namespaces()
    - Required metadata via get_base_metadata()
    - Proper response processing with feedback

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

        Args:
            zip_file: The zip file where the Common Cartridge is being built

        Returns:
            bool: True if the assessment was successfully created and added

        Raises:
            ValueError: If the block doesn't have an assessment attribute
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
        # The IMS standard resource type for discussion topics is "imsdt_xmlv1p3".
        return CommonCartridgeResourceType.DISCUSSION_TOPIC.value

    def create_cc_file_for_unit_block(self, zip_file: ZipFile) -> bool:
        forum_title = self.block.display_name or "Untitled Forum"
        forum_text = (self.block.html_content or "").strip()

        NS = "http://www.imsglobal.org/xsd/imsccv1p3/discussion_topic"
        NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
        SCHEMA_URL = "http://www.imsglobal.org/profile/cc/ccv1p3/ccv1p3_discussion_topic_v1p0.xsd"

        # Create <topics> element in the discussion_topic namespace
        topics_el = etree.Element(
            "{%s}topics" % NS,
            nsmap={
                None: NS,  # default namespace
                "xsi": NS_XSI,
            },
        )
        # Set schemaLocation (so the LMS sees we are referencing the official discussion topic XSD)
        topics_el.set(etree.QName(NS_XSI, "schemaLocation"), f"{NS} {SCHEMA_URL}")

        # Now create <topic> child
        topic_el = etree.SubElement(topics_el, "{%s}topic" % NS, identifier=str(self.block.uuid))

        title_el = etree.SubElement(topic_el, "{%s}title" % NS)
        title_el.text = forum_title

        text_el = etree.SubElement(topic_el, "{%s}text" % NS)
        text_el.text = forum_text

        # Serialize
        forum_xml_bytes = etree.tostring(
            topics_el,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

        # Write to the ZIP
        block_filename = self._block_resource_file_path()  # e.g., "folder/filename.xml"
        zip_file.writestr(block_filename, forum_xml_bytes)
        return True

    def _block_resource_file_path(self) -> str:
        """
        Override to produce a .xml filename for Forum topics
        instead of the default .html from the base class.
        """
        if not self.unit_block:
            raise ValueError("unit_block must be provided")

        block = self.unit_block.block
        folder_name = str(block.uuid)
        if block.display_name:
            filename = slugify(block.display_name) + ".xml"
        else:
            filename = f"{block.type}.xml"

        path = folder_name + "/" + filename
        if not validate_resource_path(path):
            raise ValueError(f"Invalid resource path generated: {path}")

        return path


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
