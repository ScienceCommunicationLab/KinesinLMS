import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext as _
from django_react_templatetags.mixins import RepresentationMixin

from kinesinlms.core.models import Trackable
from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block, UnitBlock
from kinesinlms.sits.constants import SimpleInteractiveToolMode, SimpleInteractiveToolType, \
    SimpleInteractiveToolSubmissionStatus
from kinesinlms.sits.schema import DiagramToolDefinition, TableToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class BaseSITProps:
    """
    This dataclass represents the properties any SIT tool
    expects to be sent from the server.
    """
    is_template: bool = False
    # We use read only for e.g. viewing in Analytics
    read_only: bool = False
    has_template: bool = False

    # For mode = BASIC
    course_id: Optional[int] = None
    course_unit_id: Optional[int] = None
    course_unit_slug: Optional[str] = None
    simple_interactive_tool_id: Optional[int] = None
    existing_simple_interactive_tool_submission_id: Optional[int] = None
    existing_simple_interactive_tool_submission: Optional[Dict] = None
    status: Optional[str] = None
    score: Optional[int] = 0
    max_score: Optional[int] = 0


@dataclass
class DiagramProps(BaseSITProps):
    """
    This dataclass represents the properties the DiagramTool
    expects to be sent from the server.
    """
    tool_type: str = SimpleInteractiveToolType.DIAGRAM.name
    # Change this to TEMPLATE if working with template.
    mode: str = SimpleInteractiveToolMode.BASIC.name
    # for mode = TEMPLATE
    simple_interactive_template_id: Optional[int] = None
    template_json: Optional[Dict] = None

    # JSON definition of tabletool...this is not the
    # student's created diagram, it's for configuring the diagram tool.
    definition: Optional[DiagramToolDefinition] = None


@dataclass
class TabletoolProps(BaseSITProps):
    """
    This dataclass represents the properties the TableTool
    expects to be sent from the server.
    """

    tool_type: str = SimpleInteractiveToolType.TABLETOOL.name

    # Change this to TEMPLATE if working with template.
    mode: str = SimpleInteractiveToolMode.BASIC.name

    # JSON definition of tabletool...this is not the
    # student's created diagram, it's for configuring the diagram tool.
    definition: Optional[TableToolDefinition] = None


class SimpleInteractiveToolTemplate(RepresentationMixin, Trackable):
    """
    A SimpleInteractiveToolTemplate describes a base layout for the tool
    that should be rendered when a student first visits the tool in the course.
    """

    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               blank=True,
                               null=True,
                               help_text=_("The author of this template"),
                               related_name='simple_interactive_tool_templates',
                               on_delete=models.CASCADE)

    tool_type = models.CharField(max_length=50,
                                 choices=[(tag.name, tag.value) for tag in SimpleInteractiveToolType],
                                 help_text=_("The type of SimpleInteractiveTool this template is for."),
                                 default=None,
                                 null=True,
                                 blank=True)

    # One reason for a unique slug is to make it easier to link
    # to this template in course import / export.
    slug = models.SlugField(max_length=40,
                            unique=True,
                            blank=True,
                            null=True,
                            help_text=_('Unique slug for template'))

    name = models.CharField(blank=True,
                            null=True,
                            max_length=200,
                            help_text=_("The name of this SimpleInteractiveTool "
                                        "template (not shown to student)."))

    description = models.TextField(_('Description of this SimpleInteractiveTool template and '
                                     'its purpose (not shown to student).'),
                                   blank=True,
                                   null=True)

    instructions = models.TextField(_('Instructions for student on how to work with  '
                                      'this particular SimpleInteractiveTool template.'),
                                    blank=True,
                                    null=True)

    # Meta-data about this SimpleInteractiveTool, used to help configure the tool
    # when loaded by the React component.
    definition = JSONField(null=True, blank=True)

    # The template_json holds the same json structure
    # that would be created by a student using the tool.
    # This json will be copied into a SimpleInteractiveToolSubmission
    # instance's json_content field to 'pre-populate' it when
    # shown to the user for the first time.
    template_json = models.JSONField(null=True,
                                     blank=True,
                                     help_text=_("A complete JSON definition of the SimpleInteractiveTool template"), )

    def __str__(self):
        return f"SimpleInteractiveToolTemplate: '{self.name}'"

    @property
    def js_component_name(self) -> str:
        if self.tool_type == SimpleInteractiveToolType.DIAGRAM.name:
            return "DiagramTemplate"
        elif self.tool_type == SimpleInteractiveToolType.TABLETOOL.name:
            return "TabletoolTemplate"
        elif self.tool_type is None:
            raise Exception("SimpleInteractiveToolTemple does not have tool_type set")
        else:
            raise NotImplemented(f'SimpleInteractiveToolTemple has an unsupported '
                                 f'tool_type : {self.tool_type}')

    def to_react_representation(self, context=None) -> Dict:
        """
        This method is used by our django-react-templatetags plugin.
        It shapes the model data for inclusion in the React component
        when included as part of a Django template. The React component
        then reads this data on startup.

        Therefore, this method should return an object that has everything
        the React component needs to render this SimpleInteractiveTool template
        for editing by staff or admin.

        :param context:
        :return:
        """

        diagram_props = DiagramProps()
        diagram_props.mode = SimpleInteractiveToolMode.TEMPLATE.name
        diagram_props.simple_interactive_template_id = self.id
        diagram_props.tool_type = self.tool_type
        diagram_props.template_json = self.template_json
        diagram_props.definition = self.definition

        # TODO: Not sure how to get a table definition when multiple
        # TODO: tables (potentially with different definitions) can be
        # TODO: linked to the same template.

        obj = asdict(diagram_props)

        if self.tool_type == SimpleInteractiveToolType.DIAGRAM.name:
            obj['can_save_without_mentor_type'] = True

        logger.info(f"Returning this obj for SimpleInteractiveToolTemplate props: {obj}")

        return obj


# noinspection PyUnresolvedReferences
class SimpleInteractiveTool(RepresentationMixin, Trackable):
    """
    SimpleInteractiveTools are special types of blocks that render
    a 'simple' interactive tool that has some basic characteristics:

    - It has a 'definition' json to describe metadata about the tool
    - It may have a link to an 'SimpleInteractiveToolTemplate' model
     instance that contains an initial state for when the student
     first views the tool (otherwise it should just be 'blank').

    We model these in a similar way to how we handle Assessments:
    We have a one-to-one relationship with block, such that this model
    holds very SimpleInteractiveTool-specific metadata above the
    more generic data held by the Block.

    Then, student submissions will be held in the SimpleInteractiveToolSubmission
    model defined in this module.
    """

    block = models.OneToOneField(Block,
                                 on_delete=models.CASCADE,
                                 related_name='simple_interactive_tool')

    name = models.CharField(max_length=400,
                            null=True,
                            blank=True)

    tool_type = models.CharField(max_length=50,
                                 choices=[(tag.name, tag.value) for tag in SimpleInteractiveToolType],
                                 default=None,
                                 null=True,
                                 blank=True)

    slug = models.SlugField(null=False,
                            blank=False,
                            unique=True,
                            allow_unicode=True)

    instructions = models.TextField(_('Instructions and/or extra information about '
                                      'this SimpleInteractiveTool to display to the student.'),
                                    blank=True,
                                    null=True)

    # Meta-data about this SimpleInteractiveTool, used to help configure the tool
    # when loaded by the React component.
    definition = JSONField(null=True, blank=True)

    template = models.ForeignKey(SimpleInteractiveToolTemplate,
                                 help_text=_("If defined, a template that describes the initial layout "
                                             "to be rendered when this SimpleInteractiveTool is first displayed."),
                                 blank=True,
                                 null=True,
                                 related_name='simple_interactive_tools',
                                 on_delete=models.SET_NULL)

    # If an SIT is 'graded' it means it counts towards
    # a milestone defined as a certain number of assessments to be completed.
    graded = models.BooleanField(default=False, null=False, blank=True)

    # Maximum score that can be earned for this SIT.
    max_score = models.IntegerField(default=1, null=False, blank=False)

    def __str__(self):
        return f"SIT (type: {self.tool_type} id: {self.id})"

    @property
    def display_name(self):
        if self.name:
            return self.name
        elif self.block.display_name:
            return self.block.display_name
        else:
            return f"Simple Interactive Tool '{self.slug}'"

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        definition = self.definition

        # Make sure json fields are valid
        if definition:
            if self.tool_type == SimpleInteractiveToolType.DIAGRAM.name:
                try:
                    DiagramToolDefinition.from_dict(definition)
                except Exception as e:
                    raise ValidationError(f"Invalid 'definition' JSON: {e}")

            elif self.tool_type == SimpleInteractiveToolType.TABLETOOL.name:
                try:
                    TableToolDefinition.from_dict(definition)
                except Exception as e:
                    raise ValidationError(f"Invalid 'definition' JSON: {e}")

            else:
                logger.warning(f"Cannot validate definition for SimpleInteractiveTool : {self} "
                               f"type: {self.tool_type} because no json schema is defined.")

    @property
    def helper_javascript_libraries(self) -> List:
        if self.tool_type:
            return SimpleInteractiveTool.get_helper_javascript_libraries(self.tool_type)
        return []

    @staticmethod
    def get_helper_javascript_libraries(tool_type: str) -> List[str]:
        """
        Return any 'helper' javascript libraries required by this SimpleInteractiveTool.
        """
        if tool_type == SimpleInteractiveToolType.DIAGRAM.name:
            return ['kinesinlms-diagrams-components.bundle.js']
        elif tool_type == SimpleInteractiveToolType.TABLETOOL.name:
            return ['kinesinlms-tabletool-components.bundle.js']
        else:
            logger.warning(f"No helper libraries defined for "
                           f"SimpleInteractiveToolType type: {tool_type} ")
            return []

    def to_react_representation(self, context=None) -> Dict:
        """
        This method is used by our django-react-templatetags plugin.
        It shapes the model data for inclusion in the React component
        when included as part of a Django template. The React component
        then reads this data (as props) on startup.

        Therefore, this method should return an object that has
        everything React component needs to render the SimpleInteractiveTool.

        A SIT should never be in a state where it doesn't have a definition.
        If it does, create a default definition for it as part of this method.

        Args:
            context
        """

        student = context['user']
        course = context.get('course')
        course_unit = context.get('course_unit', None)
        unit_block = UnitBlock.objects.get(course_unit=course_unit,
                                           block=self.block)
        read_only = unit_block.read_only
        if course.has_finished:
            read_only = True

        if course_unit:
            course_unit_id = course_unit.id
            course_unit_slug = course_unit.slug
        else:
            course_unit_id = None
            course_unit_slug = None

        if self.definition is None:
            self.definition = {}
            self.save()

        # Check for existing submitted SimpleInteractiveToolSubmission
        existing_submission = None
        try:
            existing_submission = SimpleInteractiveToolSubmission.objects.get(student=student,
                                                                              course=course,
                                                                              simple_interactive_tool=self)
        except SimpleInteractiveToolSubmission.DoesNotExist:
            pass
        except Exception as e:
            logger.exception(f"Error trying to get existing submission "
                             f"for SimpleInteractiveToolSubmission {self}. error: {e}")

        if self.template and self.template.template_json:
            # Use template if user hasn't interacted
            if not existing_submission:
                existing_submission, created = SimpleInteractiveToolSubmission.objects.get_or_create(
                    student=student,
                    course=course,
                    simple_interactive_tool=self)
            # Only use template if student hasn't done any work.
            if not existing_submission.json_content:
                existing_submission.json_content = self.template.template_json
            has_template = True
        else:
            has_template = False

        if self.tool_type == SimpleInteractiveToolType.DIAGRAM.name:
            sit_props = DiagramProps()
            # Making sure missing fields are populated with the definition default values.
            if self.definition:
                sit_props.definition = DiagramToolDefinition.from_dict(self.definition).to_dict()
            else:
                sit_props.definition = DiagramToolDefinition().to_dict()
            # only diagrams have template capability at the moment...
            sit_props.has_template = has_template
        elif self.tool_type == SimpleInteractiveToolType.TABLETOOL.name:
            sit_props = TabletoolProps()
            # Making sure missing fields are populated with the definition default values.
            sit_props.definition = TableToolDefinition.from_dict(self.definition).to_dict()
        else:
            raise Exception(f"Unrecognized SIT tool_type: {self.tool_type}")

        # Fill in props that all SITs have...
        sit_props.mode = SimpleInteractiveToolMode.BASIC.name
        sit_props.simple_interactive_tool_id = self.id
        sit_props.course_id = course.id
        sit_props.course_unit_id = course_unit_id
        sit_props.course_unit_slug = course_unit_slug
        sit_props.read_only = read_only
        sit_props.max_score = self.max_score

        if existing_submission:
            sit_props.existing_simple_interactive_tool_submission_id = existing_submission.id
            sit_props.existing_simple_interactive_tool_submission = existing_submission.json_content
            sit_props.status = existing_submission.status
            sit_props.score = existing_submission.score

        obj = asdict(sit_props)

        return obj


class SimpleInteractiveToolSubmission(Trackable):
    class Meta:
        unique_together = (('student', 'simple_interactive_tool', 'course'),)

    course = models.ForeignKey(Course,
                               null=True,
                               related_name="simple_interactive_tool_submissions",
                               on_delete=models.CASCADE
                               )

    simple_interactive_tool = models.ForeignKey(SimpleInteractiveTool,
                                                blank=False,
                                                null=False,
                                                related_name='submissions',
                                                on_delete=models.CASCADE)

    student = models.ForeignKey(settings.AUTH_USER_MODEL,
                                blank=False,
                                null=False,
                                related_name='simple_interactive_tool_submissions',
                                on_delete=models.CASCADE)

    status = models.CharField(max_length=50,
                              choices=[(tag.name, tag.value) for tag in SimpleInteractiveToolSubmissionStatus],
                              default=SimpleInteractiveToolSubmissionStatus.UNANSWERED.name,
                              null=False,
                              blank=True,
                              )

    # Score achieved by the student (<= SIT.max_score)
    score = models.PositiveIntegerField(default=1, null=False, blank=True)

    json_content = JSONField(null=True, blank=True)

    def set_status(self):
        """
        Set the status of this submission based on the json_content
        and the nature of the SIT.

        TODO:   At the moment this check is very basic. Essentially,
                if there's content, the SIT is complete.
        """
        if self.json_content and bool(self.json_content):
            self.status = SimpleInteractiveToolSubmissionStatus.COMPLETE.name
            self.score = self.simple_interactive_tool.max_score
        else:
            self.status = SimpleInteractiveToolSubmissionStatus.UNANSWERED.name
            self.score = 0
        self.save()

    def get_data_for_tracking_log(self):
        return {
            "simple_interactive_tool_id": self.simple_interactive_tool.id,
            "simple_interactive_tool_type": self.simple_interactive_tool.tool_type,
            "simple_interactive_tool_submission_id": self.id,
            "status": self.status
        }
