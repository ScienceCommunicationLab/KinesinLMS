from typing import Dict, Optional, Type

from kinesinlms.composer.blocks.panels.panels import (
    DoneIndicatorAssessmentPanelSet,
    ExternalToolViewPanelSet,
    FileResourceBlockPanelSet,
    ForumTopicPanelSet,
    HTMLBlockPanelSet,
    JupyterPanelSet,
    LongFormTextAssessmentPanelSet,
    MultipleChoiceAssessmentPanelSet,
    PanelSet,
    PollAssessmentPanelSet,
    SimpleInteractiveToolPanelSet,
    SurveyPanelSet,
    VideoBlockPanelSet,
)
from kinesinlms.learning_library.constants import AssessmentType, BlockType
from kinesinlms.learning_library.models import Block


class PanelSetBuilder:
    """
    Base builder class for creating a "panel set",
    which is simply a set of panels for editing a block.

    A panel is just a form in a tab on the block edit page.

    The idea is that many blocks will share a subset of panels
    (like a panel for editing the block's HTML content),
    so the builder will know which panels to create based on
    the block type.

    """

    def __init__(self):
        self.panel_set: Optional[PanelSet] = None

    def build_panel_set(self, block: Block):
        self.panel_set = self.create_panel_set(block)

    def create_panel_set(self, block: Block) -> PanelSet:
        raise NotImplementedError("create_panel_set must be implemented in subclasses")

    def get_panel_set(self) -> PanelSet:
        return self.panel_set


class HTMLBlockPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing an HTML block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.HTML_CONTENT.name:
            return HTMLBlockPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class FileResourceBlockPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing a FILE_RESOURCE block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.FILE_RESOURCE.name:
            return FileResourceBlockPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class SimpleInteractiveToolPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing a simple interactive tool block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
            return SimpleInteractiveToolPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class ExternalToolViewPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing an external tool view block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.EXTERNAL_TOOL_VIEW.name:
            return ExternalToolViewPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class JupyterPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing an Jupyter view block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.JUPYTER_NOTEBOOK.name:
            return JupyterPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class VideoBlockPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing a video block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.VIDEO.name:
            return VideoBlockPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class ForumTopicPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing a forum topic block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.FORUM_TOPIC.name:
            return ForumTopicPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class SurveyPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing a survey block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type == BlockType.SURVEY.name:
            return SurveyPanelSet()
        else:
            raise ValueError(f"Unsupported block type: {block.type}")


class AssessmentPanelSetBuilder(PanelSetBuilder):
    """
    Build a panel set for editing an assessment block.
    """

    def create_panel_set(self, block: Block) -> PanelSet:
        if block.type != BlockType.ASSESSMENT.name:
            raise ValueError(f"Unsupported block type: {block.type}")
        if block.assessment.type == AssessmentType.MULTIPLE_CHOICE.name:
            return MultipleChoiceAssessmentPanelSet()
        elif block.assessment.type == AssessmentType.LONG_FORM_TEXT.name:
            return LongFormTextAssessmentPanelSet()
        elif block.assessment.type == AssessmentType.DONE_INDICATOR.name:
            return DoneIndicatorAssessmentPanelSet()
        elif block.assessment.type == AssessmentType.POLL.name:
            return PollAssessmentPanelSet()
        else:
            raise ValueError(f"Unsupported assessment type: {block.assessment.type}")


class PanelSetManager:
    """
    A manager class for setting up a panel set builder
    and then building the panel set.
    (Builder pattern).

    This class and the related builders seem a little slim
    right now, but I imagine they'll grow in complexity
    as we add more block types and the panels get more complex.
    In that case I think the builder pattern will be a good fit.

    """

    def __init__(self):
        self.builder: Optional[PanelSetBuilder] = None
        self.builder_classes: Dict[str, Type[PanelSetBuilder]] = {
            BlockType.HTML_CONTENT.name: HTMLBlockPanelSetBuilder,
            BlockType.FILE_RESOURCE.name: FileResourceBlockPanelSetBuilder,
            BlockType.ASSESSMENT.name: AssessmentPanelSetBuilder,
            BlockType.VIDEO.name: VideoBlockPanelSetBuilder,
            BlockType.SURVEY.name: SurveyPanelSetBuilder,
            BlockType.FORUM_TOPIC.name: ForumTopicPanelSetBuilder,
            BlockType.SIMPLE_INTERACTIVE_TOOL.name: SimpleInteractiveToolPanelSetBuilder,
            BlockType.EXTERNAL_TOOL_VIEW.name: ExternalToolViewPanelSetBuilder,
            BlockType.JUPYTER_NOTEBOOK.name: JupyterPanelSetBuilder,
        }

    def set_builder_for_block(self, block: Block):
        """
        Set the correct builder based on the given block.
        """
        builder_class: Type[PanelSetBuilder] = self.builder_classes.get(
            block.type, None
        )
        if not builder_class:
            raise ValueError(f"Unsupported block type: {block.type}")
        builder = builder_class()
        self.block = block
        self.builder = builder

    def build_panel_set(self) -> PanelSet:
        """
        Build a panel set for the given block (and builder).
        """
        if self.builder is None:
            raise ValueError("PanelSetBuilder not set")

        self.builder.build_panel_set(self.block)
        panel_set: PanelSet = self.builder.get_panel_set()
        return panel_set
