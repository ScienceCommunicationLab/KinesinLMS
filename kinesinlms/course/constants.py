from enum import Enum


class NodeType(Enum):
    """ The types of nodes that compose a CourseTree """
    ROOT = 'root'
    MODULE = 'module'
    SECTION = 'section'
    UNIT = 'unit'

    def __str__(self):
        return self.name


class NodePurpose(Enum):
    """
    Purpose for a UNIT type CourseNode. This value is useful
    for providing more information to something like QuickNav
    without having to dig into the CourseUnit.

    NOTE: This property can be used by SECTION and MODULE
    nodes if the whole node is the same node purpose type.
    e.g. Surveys or Plans like BYRC's Roadmap.

    """

    # TODO:
    #   This *should* be the usual setting for a UNIT type CourseNode
    #   But I used LESSON below. So eventually get rid of LESSON
    #   and just use this.
    DEFAULT = "Default"

    INTRODUCTION = "Introduction"

    # This is the typical purpose of a node
    # TODO: This is poorly named, since the team
    #       refers to "sections" as "lessons"
    #       Perhaps change this to "DEFAULT"
    LESSON = "Lesson"

    SURVEY = "Surveys"

    # Extra content example: Q&A Session
    EXTRA_CONTENT = "Extra Content"

    # Plan is a page that contains a list of activities
    # that the user has completed and are now presented in a
    # comprehensive way, such that it can be reviewed and/or printed.
    PLAN = "Plan"

    # ...and anything outside 'Plan' that we can group
    # into a more generic 'Activity'
    ACTIVITY = "Activity"


class MilestoneType(Enum):
    CORRECT_ANSWERS = "Correct answers"
    VIDEO_PLAYS = "Video plays"
    FORUM_POSTS = "Forum Posts"
    SIMPLE_INTERACTIVE_TOOL_INTERACTIONS = "Simple interactive tool interactions"

    def __str__(self):
        return self.name


SIMPLE_MILESTONE_TYPES = [MilestoneType.VIDEO_PLAYS.name]


class CourseUnitType(Enum):
    """
    Describes the type of course unit. Most course units are
    just STANDARD, meaning they contain html_content and/or a
    list of blocks to render to the user.
    """

    # A 'standard' course unit, containing a list of blocks to render.
    STANDARD = 'Standard'

    # Lists all the learning objectives in the current module
    MODULE_LEARNING_OBJECTIVES = 'Module learning Objectives'

    # Lists all the learning objectives in the current section
    SECTION_LEARNING_OBJECTIVES = 'Section learning Objectives'

    # List a subset of questions from earlier in the course, rendered in read-only form.
    MY_RESPONSES = 'My Responses'

    # Show a review of questions on a printable page.
    PRINTABLE_REVIEW = "Printable Review"

    ROADMAP = "Roadmap"
