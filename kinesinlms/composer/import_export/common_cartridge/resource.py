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

from kinesinlms.composer.import_export.common_cartridge.constants import (
    CommonCartridgeExportDir,
    CommonCartridgeResourceType,
)
from kinesinlms.course.models import CourseNode, UnitBlock
from kinesinlms.learning_library.models import (
    Block,
    BlockResource,
    BlockType,
)

logger = logging.getLogger(__name__)


class CCResource(ABC):
    """
    Base class for creating a common cartridge resource.
    Our factory will use a child class to create a resource
    for a particular kind of Block.

    Args:
        ABC (_type_): _description_
    """

    block_type: str = None
    block: Block = None

    def __init__(self, block_type: str):
        self.block_type = block_type

    @abstractmethod
    def get_resource_type(self):
        pass

    def add_resource_file(
        self,
        module_node: CourseNode,
        unit_block: UnitBlock,
        zip_file: ZipFile,
    ):
        """
        This method should create a resource file for a particular type of block.
        The file should be added to the zip file.

        Args:
            module_node (CourseNode): The module node that contains the block.
            unit_block (UnitBlock): The unit block that contains the block.
            zip_file (ZipFile): The zip file to which the resource file should be added.

        Returns:
            bool:   True if the resource file was created and added successfully.
                    (otherwise an Exception should be raised)
        """
        self.block = unit_block.block
        if self.block.type != self.block_type:
            raise ValueError(
                f"Block type must be {self.block_type}, not {self.block.type}"
            )

    def add_block_resource_file(
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

    def create_resource_manifest_element(self, unit_block: UnitBlock) -> etree.Element:
        """
        Create the <resource> element for the manifest file for this block.

        (This isn't that complex yet so the entire logic is in this method.)

        Args:
            unit_block (UnitBlock): _description_

        Returns:
            etree.Element: _description_
        """
        # Create <resource/> element
        block = unit_block.block
        resource_el = etree.Element(
            "resource",
            attrib={
                "identifier": str(block.uuid),
                "type": "webcontent",
            },
        )

        if self.block_type in [BlockType.HTML_CONTENT.name, BlockType.VIDEO.name]:
            # Create nested <file/> element
            file_href = self._block_resource_file_path(unit_block)
            file_el = etree.Element("file", attrib={"href": file_href})
            resource_el.append(file_el)

        return resource_el

    def create_block_related_resource_element(
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
        resource_el = etree.Element(
            "resource",
            attrib={
                "identifier": str(resource.uuid),
                "type": "webcontent",
                "href": resource_file_path,
            },
        )

        # Create nested <file/> element
        file_el = etree.Element("file", attrib={"href": resource_file_path})
        resource_el.append(file_el)

        return resource_el

    # ~~~~~~~~~~~~~~~~~~~~~~
    # Private methods
    # ~~~~~~~~~~~~~~~~~~~~~~

    def _html_content_with_relative_resource_file_paths(
        self,
        unit_block: UnitBlock,
    ) -> str:
        """
        Returns the unit_block.block.html_content with any references to BlockResources
        updated to use their relative path in the Common Cartridge export.
        """
        html_content = unit_block.block.html_content

        for block_resource in unit_block.block.block_resources.all():
            resource_file = block_resource.resource.resource_file
            if not resource_file:
                continue

            # Convert the exported web resource path to an CC-relative path
            export_file_path = self._block_related_resource_file_path(
                block_resource=block_resource
            )
            export_file_path = re.sub(
                CommonCartridgeExportDir.WEB_RESOURCES_DIR.value,
                self.IMS_CC_ROOT_DIR,
                export_file_path,
            )

            # Replace all occurances of the resource URL with its CC-relative, exported path.
            resource_file_name = settings.MEDIA_URL + resource_file.name
            resource_match = rf'["\']{resource_file_name}["\']'
            resource_replace = f'"{export_file_path}"'

            html_content = re.sub(resource_match, resource_replace, html_content)

        return html_content

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

    def _block_related_resource_file_path(
        self,
        block_resource: BlockResource,
    ) -> str:
        uuid = str(block_resource.resource.uuid)
        folder_name = f"{CommonCartridgeExportDir.WEB_RESOURCES_DIR.value}{uuid}"
        resource = block_resource.resource
        filename = resource.resource_file.name.split("/")[-1]
        resource_export_file_path = folder_name + "/" + filename
        return resource_export_file_path


class HTMLContentCCResource(CCResource):
    def __init__(self):
        super().__init__(block_type=BlockType.HTML_CONTENT.name)

    def get_resource_type(self) -> str:
        return CommonCartridgeResourceType.WEB_CONTENT.value

    def add_resource_file(
        self,
        module_node: CourseNode,
        unit_block: UnitBlock,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for a HTML_CONTENT type block.
        Adds the file to the zip file.
        """
        super().add_resource_file(
            module_node=module_node,
            unit_block=unit_block,
            zip_file=zip_file,
        )
        html_title = (
            self.block.display_name if self.block.display_name else self.block.type
        )
        html_content = self._html_content_with_relative_resource_file_paths(unit_block)
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
        block_filename = self._block_resource_file_path(unit_block)
        zip_file.writestr(block_filename, html)

        return True

    def get_manifest_entry(self, identifier: str, resource_path: str) -> str:
        return f"""
            <resource identifier="{identifier}" type="webcontent" href="{resource_path}">
                <file href="{resource_path}"/>
            </resource>
        """


class VideoCCResource(CCResource):
    def __init__(self):
        super().__init__(block_type=BlockType.VIDEO.name)

    def get_resource_type(self) -> str:
        return "imswl_xmlv1p3"

    def add_resource_file(
        self,
        module_node: CourseNode,  # noqa: F841
        unit_block: UnitBlock,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for a VIDEO type block.
        Adds the file to the zip file.
        """
        super().add_resource_file(
            module_node=module_node,
            unit_block=unit_block,
            zip_file=zip_file,
        )
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

        block_filename = self._block_resource_file_path(unit_block)
        zip_file.writestr(block_filename, html)

        return True

    def get_manifest_entry(self, identifier: str, resource_path: str) -> str:
        return f"""
            <resource identifier="{identifier}" type="webcontent" href="{resource_path}">
                <file href="{resource_path}"/>
            </resource>
        """


class AssessmentCCResource(CCResource):
    def __init__(self):
        super().__init__(block_type=BlockType.ASSESSMENT.name)

    def get_resource_type(self) -> str:
        return CommonCartridgeResourceType.ASSIGNMENT.value

    def add_resource_file(
        self,
        module_node: CourseNode,  # noqa: F841
        unit_block: UnitBlock,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for an ASSESSMENT type block.
        Adds the file to the zip file.
        """
        super().add_resource_file(
            module_node=module_node,
            unit_block=unit_block,
            zip_file=zip_file,
        )
        logger.warning(f"Assessment block export not yet implemented: {self.block}")


class ForumTopicCCResource(CCResource):
    def __init__(self):
        super().__init__(block_type=BlockType.FORUM_TOPIC.name)

    def get_resource_type(self) -> str:
        return CommonCartridgeResourceType.DISCUSSION_TOPIC.value

    def add_resource_file(
        self,
        module_node: CourseNode,  # noqa: F841
        unit_block: UnitBlock,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for an FORUM_TOPIC type block.
        Adds the file to the zip file.
        """
        super().add_resource_file(
            module_node=module_node,
            unit_block=unit_block,
            zip_file=zip_file,
        )
        logger.warning(f"Assessment block export not yet implemented: {self.block}")


class SimpleInteractiveToolCCResource(CCResource):
    def __init__(self):
        super().__init__(block_type=BlockType.SIMPLE_INTERACTIVE_TOOL.name)

    def get_resource_type(self) -> str:
        return CommonCartridgeResourceType.ASSIGNMENT.value

    def add_resource_file(
        self,
        module_node: CourseNode,  # noqa: F841
        unit_block: UnitBlock,
        zip_file: ZipFile,
    ) -> bool:
        """
        Creates a Common Cartridge resource file for an SIMPLE_INTERACTIVE_TOOL type block.
        Adds the file to the zip file.
        """
        super().add_resource_file(
            module_node=module_node,
            unit_block=unit_block,
            zip_file=zip_file,
        )
        logger.warning(f"Assessment block export not yet implemented: {self.block}")


class JupyterNotebookCCResource(CCResource):
    def __init__(self):
        super().__init__(block_type=BlockType.JUPYTER_NOTEBOOK.name)

    def get_resource_type(self) -> str:
        return CommonCartridgeResourceType.ASSIGNMENT.value

        def add_resource_file(
            self,
            module_node: CourseNode,  # noqa: F841
            unit_block: UnitBlock,
            zip_file: ZipFile,
        ) -> bool:
            """
            Creates a Common Cartridge resource file for an JUPYTER_NOTEBOOK type block.
            Adds the file to the zip file.
            """
            super().add_resource_file(unit_block, zip_file)
            logger.warning(f"Assessment block export not yet implemented: {self.block}")
