import logging

from kinesinlms.composer.import_export.common_cartridge.resource import (
    AssessmentCCResource,
    CCResource,
    ForumTopicCCResource,
    HTMLContentCCResource,
    JupyterNotebookCCResource,
    SimpleInteractiveToolCCResource,
    VideoCCResource,
)
from kinesinlms.course.models import BlockType

logger = logging.getLogger(__name__)


class CCResourceFactory:
    """Factory for creating the appropriate resource handler for each block type"""

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
    def create_resource_handler(cls, block_type: str) -> CCResource:
        handler_class = cls.RESOURCE_HANDLERS.get(block_type)
        if not handler_class:
            raise ValueError(f"Unsupported block type: {block_type}")
        return handler_class()
