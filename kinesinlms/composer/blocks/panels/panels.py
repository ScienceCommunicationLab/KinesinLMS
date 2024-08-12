"""
Classes for describing 'panels' for editing blocks.

A panel is simply a single Django form for a portion of a block's data. The panel
is shown in a tab in the block editing UI in composer.

A panelset is a group of panels that are shown together in a block editing UI
for a specific type of block. A panelset is the complete UI for editing a block.

Some panels might have fields that are very specific to a block type (e.g. a YouTube URL
for a VIDEO type block), or more generic (block settings, resources, etc.).
So ideally some panels are used in multiple panel sets.

A panel might be a regular Django form, or it might be a UI that uses HTMx to update fields.

"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Type, Optional

from kinesinlms.composer.blocks.forms.base import BasePanelForm
from kinesinlms.composer.blocks.panels.forms import (
    MultipleChoiceAssessmentPanelForm,
    HTMLBlockPanelForm,
    BlockMetaForm,
    SurveyPanelForm,
    VideoContentPanelForm,
    LongFormTextAssessmentPanelForm,
    ForumTopicPanelForm,
    DoneIndicatorAssessmentPanelForm,
    SITDetailsPanelForm,
    ExternalToolViewPanelForm,
    PollAssessmentPanelForm,
)
from kinesinlms.learning_library.constants import BlockType, AssessmentType


class PanelType(Enum):
    DJANGO_FORM = "Django form"
    HTMX = "HTMx"


@dataclass()
class PanelTab:
    """
    Describes a 'tab' for a panel set.
    """

    label: str = ""
    url: str = ""
    panel_slug: str = ""


class Panel:
    """
    Describes a 'panel', which is a view for editing a particular
    subset of block attributes. A panel provides a UI for editing
    a portion of a block or block-related model (like Assessment).

    The panel may enable editing through regular Django forms, or
    through HTMx-based operations.
    """

    def __init__(self):
        self.slug: Optional[str] = None
        self.label: Optional[str] = None
        self.form_class: Optional[Type[BasePanelForm]] = None
        self.form: Optional[BasePanelForm] = None
        self.panel_type: str = PanelType.DJANGO_FORM.name
        self.template_name: str = "composer/blocks/panels/base_block_edit_panel.html"

    @property
    def url(self) -> str:
        return ""


class BlockSettingsPanel(Panel):
    """
    Describes a 'panel' for editing the basic 'meta' properties
    of a block, like slug, or title.

    Other more general properties might be set here, like
    learning objectives or tags.
    """

    def __init__(self):
        super().__init__()
        self.label = "Block Settings"
        self.slug = "BLOCK_SETTINGS"
        self.form_class = BlockMetaForm


class BlockResourcePanel(Panel):
    """
    Describes a 'panel' for adding resources to a block
    """

    def __init__(self):
        super().__init__()
        self.label = "Resources"
        self.slug = "BLOCK_RESOURCES"
        self.form_class = None
        self.panel_type = PanelType.HTMX.name
        self.template_name = "composer/blocks/panels/block_resource_panel.html"


class HTMLContentPanel(Panel):
    """
    Describes a 'panel' for editing the HTML content of a block.
    """

    def __init__(self):
        super().__init__()
        self.label = "HTML Content"
        self.slug = BlockType.HTML_CONTENT.name
        self.form_class = HTMLBlockPanelForm


class MultipleChoiceContentPanel(Panel):
    """
    Shows the questions and 'correct' answers information for a multiple choice
    assessment block.
    """

    def __init__(self):
        super().__init__()
        self.label = "Multiple Choice"
        self.slug = AssessmentType.MULTIPLE_CHOICE.name
        self.form_class = MultipleChoiceAssessmentPanelForm
        self.template_name = (
            "composer/blocks/panels/multiple_choice_questions_panel.html"
        )


class LongFormTextAssessmentPanel(Panel):
    """
    Shows the question and any other configuration info
    for a 'long form' text assessment block.
    """

    def __init__(self):
        super().__init__()
        self.label = "Long-form Text Assessment"
        self.slug = AssessmentType.LONG_FORM_TEXT.name
        self.form_class = LongFormTextAssessmentPanelForm


class DoneIndicatorAssessmentPanel(Panel):
    """
    Shows a panel for configuring the "Done" indicator.
    """

    def __init__(self):
        super().__init__()
        self.label = "Done Indicator Assessment"
        self.slug = AssessmentType.DONE_INDICATOR.name
        self.form_class = DoneIndicatorAssessmentPanelForm


class PollAssessmentPanel(Panel):
    """
    Shows a panel for configuring a "Poll" assessment.
    """

    def __init__(self):
        super().__init__()
        self.label = "Poll Assessment"
        self.slug = AssessmentType.POLL.name
        self.form_class = PollAssessmentPanelForm
        self.template_name = "composer/blocks/panels/poll_panel.html"


class VideoContentPanel(Panel):
    """
    Describes a 'panel' for editing a 'Video' block
    """

    def __init__(self):
        super().__init__()
        self.label = "Video Content"
        self.slug = BlockType.VIDEO.name
        self.form_class = VideoContentPanelForm


class SITDetailsPanel(Panel):
    """
    Describes a 'panel' for editing a 'Simple Interactive Tool' block
    """

    def __init__(self):
        super().__init__()
        self.label = "Simple Interactive Tool"
        self.slug = BlockType.SIMPLE_INTERACTIVE_TOOL.name
        self.form_class = SITDetailsPanelForm


class ExternalToolViewPanel(Panel):
    """
    Describes a 'panel' for editing an 'External Tool View' block
    """

    def __init__(self):
        super().__init__()
        self.label = "External Tool View"
        self.slug = BlockType.EXTERNAL_TOOL_VIEW.name
        self.form_class = ExternalToolViewPanelForm


class ForumTopicPanel(Panel):
    """
    Describes a panel for editing a FORUM_TOPIC block.
    """

    def __init__(self):
        super().__init__()
        self.label = "Forum Topic"
        self.slug = BlockType.FORUM_TOPIC.name
        self.form_class = ForumTopicPanelForm
        self.panel_type: str = PanelType.DJANGO_FORM.name
        self.template_name = "composer/blocks/panels/forum_topic_panel.html"


class SurveyPanel(Panel):
    """
    Describes a panel for editing a SURVEY block.
    """

    def __init__(self):
        super().__init__()
        self.label = "Survey"
        self.slug = BlockType.SURVEY.name
        self.form_class = SurveyPanelForm
        self.panel_type: str = PanelType.DJANGO_FORM.name
        self.template_name = "composer/blocks/panels/survey_panel.html"


class PanelSet:
    """
    Describes a series of 'panels' for editing a block.
    A panel is just a form shown on a tab in a block editing UI.

    A panel set shouldn't be created directly, but rather should
    be created by a PanelSetBuilder.
    """

    def __init__(self, *args, **kwargs):
        self.restrict_block_types: List[BlockType] = []
        self.panels: List[Panel] = []
        self._current_panel: Optional[Panel] = None

    def get_panel_by_slug(self, slug: str) -> Optional[Panel]:
        for panel in self.panels:
            if panel.slug == slug:
                return panel
        return None

    @property
    def tabs(self) -> List[PanelTab]:
        """
        Returns a list of PanelTab objects, which describe the tabs
        that should be displayed for this panel set.
        """
        tabs: List[PanelTab] = [
            PanelTab(label=panel.label, url=panel.url, panel_slug=panel.slug)
            for panel in self.panels
        ]
        return tabs

    def set_current_panel(self, slug: str):
        for panel in self.panels:
            if panel.slug == slug:
                self._current_panel = panel
                break
        return self._current_panel

    @property
    def current_panel(self) -> Panel:
        """
        Returns the current panel, based on the current request.
        """
        if self._current_panel is None:
            self._current_panel = self.panels[0]
        return self._current_panel


class VideoBlockPanelSet(PanelSet):
    """
    Panel set for editing a VIDEO block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            VideoContentPanel(),
            BlockResourcePanel(),
            BlockSettingsPanel(),
        ]


class FileResourceBlockPanelSet(PanelSet):
    """
    Panel set for editing a FILE_RESOURCE block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            BlockResourcePanel(),
        ]


class SimpleInteractiveToolPanelSet(PanelSet):
    """
    Panel set for editing a SIMPLE_INTERACTIVE_TOOL block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            SITDetailsPanel(),
            HTMLContentPanel(),
            BlockSettingsPanel(),
        ]


class ExternalToolViewPanelSet(PanelSet):
    """
    Panel set for editing an EXTERNAL_TOOL_VIEW block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [ExternalToolViewPanel(), BlockSettingsPanel()]


class HTMLBlockPanelSet(PanelSet):
    """
    Panel set for editing an HTML_CONTENT block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            HTMLContentPanel(),
            BlockResourcePanel(),
            BlockSettingsPanel(),
        ]


class MultipleChoiceAssessmentPanelSet(PanelSet):
    """
    Panel set for editing an assessment block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            MultipleChoiceContentPanel(),
            HTMLContentPanel(),
            BlockResourcePanel(),
            BlockSettingsPanel(),
        ]


class LongFormTextAssessmentPanelSet(PanelSet):
    """
    Panel set for editing an assessment block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            LongFormTextAssessmentPanel(),
            HTMLContentPanel(),
            BlockResourcePanel(),
            BlockSettingsPanel(),
        ]


class DoneIndicatorAssessmentPanelSet(PanelSet):
    """
    Panel set for editing a "Done indicator" assessment block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [
            DoneIndicatorAssessmentPanel(),
            HTMLContentPanel(),
            BlockSettingsPanel(),
        ]


class PollAssessmentPanelSet(PanelSet):
    """
    Panel set for editing a "Poll" assessment block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [PollAssessmentPanel(), HTMLContentPanel(), BlockSettingsPanel()]


class ForumTopicPanelSet(PanelSet):
    """
    Panel set for editing a FORUM_TOPIC block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [ForumTopicPanel(), BlockSettingsPanel()]


class SurveyPanelSet(PanelSet):
    """
    Panel set for editing a SURVEY block.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = [SurveyPanel(), BlockSettingsPanel()]
