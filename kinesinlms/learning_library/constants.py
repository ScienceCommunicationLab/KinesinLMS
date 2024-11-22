from enum import Enum


class BlockType(Enum):
    VIDEO = "Video"
    HTML_CONTENT = "HTML Content"
    FILE_RESOURCE = (
        "File Resource"  # Simple block that provides access to a file resource
    )
    CALLOUT = "Callout"
    ANSWER_LIST = "Answer List"
    ASSESSMENT = "Assessment"
    FORUM_TOPIC = "Forum Topic"
    SIMPLE_INTERACTIVE_TOOL = "Simple interactive tool"
    SURVEY = "Survey"
    JUPYTER_NOTEBOOK = "Jupyter notebook"
    # Not sure what to call all the different things that might
    # be exposed by an external tool (document, exercise, interaction, notebook, etc.)
    # so going with "view"...
    EXTERNAL_TOOL_VIEW = "External tool view"

    @classmethod
    def get_single_parent_type_names(cls) -> list:
        """The types of blocks that can only have one parent"""
        return [BlockType.ASSESSMENT.name, BlockType.FORUM_TOPIC.name]

    @classmethod
    def valid_types_for_composer(cls) -> list[Enum]:
        """The types of blocks that can be added to a course in composer"""
        # Right now that means all block types.
        return [item for item in BlockType]

    @classmethod
    def has_single_parent(cls, block_type: str) -> bool:
        single_parent_types = BlockType.get_single_parent_type_names()
        return block_type in single_parent_types

    def __str__(self):
        return self.name


class ContentFormatType(Enum):
    """
    Format type of content (e.g. content hosted in Block's html_content field.)
    """

    HTML = "HTML"
    MARKDOWN = "Markdown"
    PLAIN_TEXT = "Plain text"


class VideoPlayerType(Enum):
    """
    This constant is held in the json_content
    'player_type' field in Blocks of type VIDEO.
    Right now we only support YouTube...
    """

    YOUTUBE = "YouTube"


class LibraryItemType(Enum):
    BLOCK = "block"
    UNIT = "unit"
    # could there be other types?....


class ResourceType(Enum):
    """
    A resource is a file that is associated with a block.
    Right now that just means images and video transcripts.
    """

    GENERIC = "Generic"
    IMAGE = "Image"
    VIDEO_TRANSCRIPT = "Video transcript"
    JUPYTER_NOTEBOOK = "Jupyter Notebook"
    SQLITE = "SQLITE file"
    CSV = "CSV file"


class BlockStatus(Enum):
    """
    # TODO:
    #   This is just a placeholder for now.
    #   We don't have ability to do draft vs. published
    """

    DRAFT = "Draft"
    PUBLISHED = "Published"


class AnswerStatus(Enum):
    """
    States that an answer can move through.
    1) Always starts an UNANSWERED
    2) Cannot return to UNANSWERED after first submission
    """

    UNANSWERED = "Unanswered"
    INCOMPLETE = "Incomplete"

    # Answers that aren't correct or incorrect are marked
    # as complete when a student answers them.
    COMPLETE = "Complete"
    # Answers that have a correct or incorrect answer
    # should have one of these two if student answers.
    CORRECT = "Correct"
    INCORRECT = "Incorrect"

    def __str__(self):
        return self.name


# List of AnswerStatus which mark a SubmittedAnswer as "done".
ANSWER_STATUS_FINISHED = [
    AnswerStatus.CORRECT.name,
    AnswerStatus.COMPLETE.name,
]


class AssessmentType(Enum):
    LONG_FORM_TEXT = "Long-form text"
    MULTIPLE_CHOICE = "Multiple choice"
    POLL = "Poll"
    DONE_INDICATOR = "Done indicator"

    @classmethod
    def has_name(cls, name):
        return name in [item.name for item in AssessmentType]

    def __str__(self):
        return self.name


class CalloutType(object):
    # We don't define a video callout, as that information
    # is contained directly in a Video node.

    # NOTE: Callout types must not have spaces, because
    # we use the string to also set custom styles via css
    # e.g. callout-recommended_reading

    RECOMMENDED_READING = "reading"
    DISCUSSION = "discussion"

    # Other ideas are : hint, tip, etc.

    @staticmethod
    def get_callout_types():
        return [CalloutType.RECOMMENDED_READING, CalloutType.DISCUSSION]


class BlockViewContext(Enum):
    """
    Context a block is being viewed in.
    """

    # COURSE is presumed when not set
    COURSE = "course"
    LIBRARY = "library"
    COMPOSER = "composer"


class BlockViewMode(Enum):
    """
    Viewing mode for block.
    """

    # ENABLED is presumed when not set
    ACTIVE = "active"
    READ_ONLY = "read only"

    def __str__(self):
        return self.name
