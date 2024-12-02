import logging

from kinesinlms.composer.import_export.common_cartridge.resource import (
    AssessmentCCResource,
    CCHandler,
    ForumTopicCCResource,
    HTMLContentCCResource,
    JupyterNotebookCCResource,
    SimpleInteractiveToolCCResource,
    VideoCCResource,
)
from kinesinlms.course.models import BlockType, UnitBlock

logger = logging.getLogger(__name__)


class CCHandlerFactory:
    """
    Factory for creating the appropriate <resource/> elements and resources files
    for each block type that appears in a Unit.

    """

    RESOURCE_HANDLERS = {
        BlockType.HTML_CONTENT.name: HTMLContentCCResource,
        BlockType.VIDEO.name: VideoCCResource,
        BlockType.ASSESSMENT.name: AssessmentCCResource,
        BlockType.FORUM_TOPIC.name: ForumTopicCCResource,
        BlockType.SIMPLE_INTERACTIVE_TOOL.name: SimpleInteractiveToolCCResource,
        BlockType.JUPYTER_NOTEBOOK.name: JupyterNotebookCCResource,
        # Add other block types here
    }

    @classmethod
    def create_cc_handler(cls, unit_block: UnitBlock) -> CCHandler:
        handler_class = cls.RESOURCE_HANDLERS.get(unit_block.block.type)
        if not handler_class:
            raise ValueError(f"Unsupported block type: {unit_block.block.type}")
        return handler_class()
