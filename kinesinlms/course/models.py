import logging
import uuid
from enum import Enum
from typing import List, Optional

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, JSONField, Q, QuerySet
from django.db.models.fields import DateTimeField, TextField
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_react_templatetags.mixins import RepresentationMixin
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from taggit.managers import TaggableManager

from kinesinlms.badges.models import BadgeAssertion, BadgeClass
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.core.models import Trackable
from kinesinlms.course.constants import (
    CourseUnitType,
    MilestoneType,
    NodePurpose,
    NodeType,
)
from kinesinlms.course.schema import MY_RESPONSES_SCHEMA, PRINTABLE_REVIEW_SCHEMA
from kinesinlms.email_automation.notifiers import EmailAutomationNotifier
from kinesinlms.forum.models import CohortForumGroup
from kinesinlms.forum.utils import get_forum_service
from kinesinlms.institutions.models import Institution
from kinesinlms.learning_library.constants import (
    ANSWER_STATUS_FINISHED,
    ContentFormatType,
)
from kinesinlms.learning_library.models import (
    Block,
    BlockStatus,
    BlockType,
    LearningObjective,
    LibraryItem,
    UnitBlock,
)
from kinesinlms.learning_library.utils import get_learning_objectives_for_course
from kinesinlms.users.models import User

logger = logging.getLogger(__name__)


class CohortType(Enum):
    DEFAULT = "default"
    RANDOM = "random"
    CUSTOM = "custom"


class CourseManager(models.Manager):
    def get_by_natural_key(self, slug, run):
        return self.get(slug=slug, run=run)


class CourseUnit(Trackable):
    """
    A CourseUnit stacks up course-independent blocks into
    a course-specific unit. Because they're associated with a
    specific course, we can attach things that need to be associated
    to the course through the unit they appear in, like student
    answers on assessments.
    """

    tags = TaggableManager(
        blank=True,
        help_text=_("Tags for this course unit"),
    )

    uuid = models.UUIDField(
        primary_key=False,
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    # Why does the CourseUnit model have a slug?
    # CourseUnit slugs are meant to provide an easy, intelligible, and **unique**
    # identifier for authoring, analytics, etc.
    #
    # Course unit slugs are unique across the site.
    # If the course unit slugs were not unique across the site, then a course author
    # couldn't reliably use the slug when trying to add an existing course unit into a
    # new course.
    #
    # You might think: "Wait, that's a problem because I might have multiple CourseUnits
    # in different courses that I want to have the same slug called 'introduction'."
    #
    # That's ok, because the slugs here are not shown to users, as course nodes are,
    # since CourseNode is the model whose slug is used for things like URLs. So just
    # come up with a unique slug like demo-sp-introduction
    #
    # This CourseUnit model also has an uuid unique identifier, but that is
    # mainly for machines, for example when the importer links to existing course units
    # when importing a json representation of a course.

    slug = models.SlugField(
        max_length=200,
        null=True,
        blank=True,
        allow_unicode=True,
        unique=True,
        db_index=True,
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in CourseUnitType],
        default=CourseUnitType.STANDARD.name,
        null=False,
        blank=False,
        db_index=True,
    )

    # Convenience relationship, not normalized as Course is also linked to through
    # the CourseNode MPTT tree. But this direct relation will be helpful in queries
    # like 'get all CourseUnits in this course' or 'get parent course for CourseUnit'
    # because you don't have to walk the MPTT tree to get the course.
    course = models.ForeignKey(
        "Course",
        related_name="course_units",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )

    display_name = models.CharField(
        max_length=400,
        null=True,
        blank=True,
        help_text="Appears at the top of a course unit.",
    )

    # Short description to be used when listing units
    # outside of course or for staff composing a course.
    short_description = models.TextField(null=True, blank=True)

    contents = models.ManyToManyField(
        "learning_library.Block",
        through="learning_library.UnitBlock",
        related_name="units",
    )

    # Prevent this Unit from being copied to the library.
    course_only = models.BooleanField(default=False, null=False, blank=False)

    # HTML content for this unit.
    html_content = models.TextField(null=True, blank=True)

    # Format type of html_content. This is used to determine how to render
    # the html_content field.
    html_content_type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in ContentFormatType],
        default=ContentFormatType.HTML.name,
        null=False,
        blank=False,
    )

    enable_template_tags = models.BooleanField(
        default=True,
        null=False,
        blank=True,
        help_text="Enables a limited number of template tags in " "this model's html_content field.",
    )

    # JSON content for this unit. This holds different data depending
    # on the unit type. We define JSON schemas to validate incoming
    # data and really just help us remember the shape of each type's data.
    # Block renders or React-based components know what to expect for
    # a particular block type.
    json_content = JSONField(null=True, blank=True)

    # Status for this block. At the moment that just means 'draft' or
    # 'published', so this field is a way of staging content for the library.
    status = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in BlockStatus],
        default=BlockStatus.PUBLISHED.name,
        null=False,
        blank=False,
    )

    json_content_validators = {
        CourseUnitType.PRINTABLE_REVIEW.name: PRINTABLE_REVIEW_SCHEMA,
        CourseUnitType.MY_RESPONSES.name: MY_RESPONSES_SCHEMA,
    }

    @property
    def ordered_contents(self) -> List[Block]:
        """
        DMcQ: For some reason, even though I've defined ordering in my
        join table UnitBlock, when I access 'unit.contents' from e.g. the quicknav
        , the contents are not ordered. So using this method as a temporary way
        to make sure I'm getting ordered contents...
        """
        contents = [unit_block.block for unit_block in self.unit_blocks.all()]
        return contents

    @property
    def is_released(self) -> bool:
        """
        Has this unit been released in the course yet.
        Since a CourseUnit can appear multiple times in a course
        we look for the first 'true'.

        Returns:
            Boolean
        """
        course_nodes: List[CourseNode] = self.course_nodes.all()
        for course_node in course_nodes:
            if course_node.is_released:
                return True
        return False

    def learning_objectives(self) -> List[LearningObjective]:
        """
        Gather and return all learning objectives for all
        blocks in this unit.
        """
        block_ids = [item.block.id for item in self.unit_blocks.all()]
        learning_objectives = LearningObjective.objects.filter(blocks__id__in=block_ids).distinct().all()
        return learning_objectives

    def get_url(self, course):
        """
        Returns the URL for this CourseUnit in
        a particular course it appears in.

        A CourseUnit can appear in more than one
        course, so use the course argument to disambiguate.
        (Otherwise, use the 'originating' course as
        defined in this model's 'course' property.)

        :param course:
        :return:
        """
        if not course:
            course = self.course

        for course_node in self.course_nodes.all():
            c = course_node.get_course()
            if c == course:
                node_url = course_node.node_url
                logger.debug(f"Found node URL {node_url} for CourseUnit {self} ")
                return course_node.node_url

        return None

    def delete_block(self, block: Block):
        """
        Delete a block from a course unit.

        If this block is not used in any other CourseUnits, and is not a library
        item, delete it for good and clean up all related models.
        """

        logger.info(f"Deleting block: {block}...")

        try:
            delete_unit_block = UnitBlock.objects.get(block=block, course_unit=self)
        except UnitBlock.DoesNotExist:
            delete_unit_block = None

        # Delete associated models based on block type
        if block.type == BlockType.FORUM_TOPIC.name:
            # If the block is a forum topic, we need to delete the forum topic
            # as well as the block.
            forum_service = get_forum_service()
            for forum_topic in block.forum_topics.all():
                forum_service.delete_topic(forum_topic)

        # Delete the associated unit_block, and while doing so reindex the remaining unit_blocks.
        if delete_unit_block:
            unit_blocks = self.unit_blocks.order_by("block_order").all()
            index = 0
            for unit_block in unit_blocks:
                if unit_block == delete_unit_block:
                    unit_block.delete()
                else:
                    unit_block.block_order = index
                    unit_block.save()
                    index += 1

        # If this Block does not exist in other CourseUnits nor in
        # the Block library, delete it for good.

        other_unit_block_instances = UnitBlock.objects.filter(block=block)
        learning_library_instances = LibraryItem.objects.filter(block=block)
        if other_unit_block_instances.count() == 0 and learning_library_instances.count() == 0:
            logger.warning(
                f"Deleting actual block : {block} since it is not used in " f"any course nor in the library."
            )
            block.delete()

        logger.info("  - block deleted.")


class CourseNode(MPTTModel):
    """
    This is a modified preorder tree traversal (via MPTT library) that
    contains the structure of a course. This model does not contain
    actual learning content, but does have a relation that points to
    a CourseUnit, which does contain learning content.

    CourseNodes can point to the same CourseUnit in different parts of the course,
    which is nice if you want the student to revisit the same unit multiple times
    in a course, e.g. to build up a set of answers over time. (At least, it seemed
    like a nice feature of this structure but perhaps this isn't practical usage.)

    Don't forget:
    -   to update the CourseNodeSerializer if you make changes to this
        model and want to have those changes available in a template (like
        the QuickNav) or a front-end component.
    -   to bust the cache if you make changes to content or structure of your course nodes.
    """

    class MPTTMeta:
        order_insertion_by = ["display_sequence"]

    # Some slug names are disallowed,
    # since it would clash with REST API endpoints
    # for certain features, like certificate.
    DISALLOWED_NODE_SLUG_NAMES = [
        "certificate",
        "export",
        "progress",
        "extra",
        "bookmarks",
        "custom_app",
        "resource",
        "forum_topics",
    ]

    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    # The CourseNode 'type' property defines its place in our generic structure of Module > Section > Unit
    # So this property is more for organizing content then telling the user what this
    # part of the course is about. (That's defined in the next property "purpose".)
    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in NodeType],
        default=NodeType.ROOT,
        null=False,
        blank=False,
    )

    # The Node 'purpose' property helps define what this node is doing within course,
    # e.g. serving basic content, a container for surveys, an introduction, etc.
    # Null means no defined purpose. We really only use this field for UNIT nodes.
    purpose = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in NodePurpose],
        default=None,
        null=True,
        blank=True,
    )

    # The name rendered in the navigation.
    display_name = models.CharField(max_length=400, null=True, blank=True)

    # Note that for *root* nodes, the slug is set to the course token
    # (not the course slug). So for course with slug=TEST and run=SP,
    # you'll see a slug here like TEST_SP (the course token)
    slug = models.SlugField(max_length=200, null=False, blank=True, allow_unicode=True)

    # The date and time this node should be made available to the student.
    release_datetime = DateTimeField(null=True, blank=True)

    # TODO:
    #   display_sequence and content_index are terrible names.
    #   If ever possible, I should change them to something like
    #   'index' and 'display_index' to make it clear one is fundamental
    #   to indexing and one is for showing to the student.

    # The content_index is the number shown to the user as part of this
    # node's name or other kind of label. If it's null, nothing is shown,
    # which keeps your mental model of the world intact.
    content_index = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="The number to show next to a node when rendered in navigation. "
        "This is separate from display_sequence as sometimes e.g. "
        "some modules do not have a number.",
    )

    # The display sequence controls the ordering of this node amongst its immediate peers
    # Because it's used for ordering within a parent, we can't reliably use it
    # also for labels (that may only make sense at the course level)
    # like "Lesson 3"...hence the content_index property above.
    display_sequence = models.IntegerField(
        default=0,
        null=False,
        blank=False,
        help_text="Ordering index for this node. Nodes will be sorted by " "this value when shown in navigation.",
    )

    # Theoretically, a CourseNode at any level could have a link in this 'unit' field
    # to a CourseUnit. But if it does, this CourseNode shouldn't have children, i.e. it should
    # be a leaf node.
    # For now, though, we should stick with the basic convention: Module, Section, Unit,
    # with only 'Unit' nodes having an actual unit (with the link via this property).
    unit = models.ForeignKey(
        CourseUnit,
        on_delete=models.CASCADE,
        related_name="course_nodes",
        null=True,
        blank=True,
    )

    @property
    def node_url(self):
        """
        Get a complete URL to this nodes position in the course.
        Does not have to point to a unit. There may be routing logic downstream
        that forwards a shorter URL (e.g. to a module) to the first displayable
        thing...which at the moment can only be a unit.
        :return:
        """
        ancestors = self.get_ancestors(include_self=True).all()
        root = ancestors[0]
        remaining_nodes = ancestors[1:]
        course = root.course
        path = f"{course.course_url}"
        for course_node in remaining_nodes:
            path += f"{course_node.slug}/"
        return path

    def get_course(self):
        root = self.get_root()
        course = root.course
        return course

    def clean(self):
        if self.is_leaf_node():
            # commenting out this check because it prevents me from adding nodes other than Unit-type
            # when building new contents
            # if self.type != NodeType.UNIT.name:
            #    raise ValidationError("Leaf nodes must be 'unit' NodeType")
            if self.type == NodeType.UNIT.name and not self.unit:
                raise ValidationError("'unit' NodeType is missing reference to a 'unit' block")
        else:
            # is not a leaf node, so ...
            if self.type == NodeType.UNIT.name:
                raise ValidationError("'unit' type NodeTypes must be leaf nodes.")
        if self.parent and self.parent.unit is not None:
            raise ValidationError("Can't have parent node that has a 'Unit' block assigned")

        # CourseNodes have to have a slug because we use it in the URL path
        if not self.slug:
            raise ValidationError("CourseNode must have a slug")

        if self.slug in CourseNode.DISALLOWED_NODE_SLUG_NAMES:
            raise ValidationError("Invalid slug name")

    @property
    def is_released(self) -> bool:
        """
        Determine whether this CourseNode is released.
        """
        if not self.release_datetime:
            return True
        try:
            current_datetime = now()
            logger.info(f"self_release_datetime: {self.release_datetime}")
            logger.info(f"now() {current_datetime}")
            # The dates compared here should both be in UTC, thanks to Django magic from USE_TZ=True
            released = self.release_datetime <= current_datetime
        except Exception:
            logger.exception("Could not determine is_released(). Returning True.")
            released = True
        return released

    @property
    def is_unit(self):
        return self.type == NodeType.UNIT.name

    @property
    def link_enabled(self):
        """
        Determines whether a link should be shown for this node.
        We only show a link if the node is a unit.
        We used to not show the link if the node is not released,
        but now I do show content for an unreleased node
        (it just reads something like 'unit is not yet released' )
        """
        enabled = self.is_unit
        return enabled

    @property
    def content_token(self) -> str:
        """
        The content_token is a small token used in QuickNav
        that helps the user understand what the node it.

        It usually contains the first letter of the node's
        purpose, like "M" for module or "S" for section.
        And it has an index if the content_index is defined,
        like "L8" for lesson 8.

        Sometimes the admin might want to override the use
        of the first letter of the node's purpose. Use
        the node_symbol property to do that.

        :return: String
        """
        token = ""
        try:
            if self.type == NodeType.MODULE.name:
                token = "M"
                if self.content_index is not None:
                    token = token + str(self.content_index)
            elif self.type == NodeType.SECTION.name:
                # Admin can override the default
                # symbol, so use the override if present
                token = "S"
                if self.content_index is not None:
                    token = token + str(self.content_index)
        except Exception:
            logger.exception("CourseNode content_token: couldn't generate content_token.")
        return token

    @property
    def content_tooltip(self) -> str:
        """
        The content_tooltip is meant for the tooltip in things like QuickNav.

        Returns:
            String for tooltip
        """

        if self.type == NodeType.MODULE.name:
            if self.content_index:
                module_label = f"<br/>{self.content_index} : {self.display_name}"
            else:
                module_label = f"<br/>{self.display_name}"
            tooltip = f"<em>Module</em>{module_label}"
            return tooltip

        elif self.type == NodeType.SECTION.name:
            if self.content_index:
                section_label = f"<br/><br/>{self.content_index} : {self.display_name}"
            else:
                section_label = f"<br/>{self.display_name}"
            tooltip = f"<em>Section</em>{section_label}"
            return tooltip
        elif self.type == NodeType.UNIT.name:
            tooltip = f"<em>Unit</em><br/>{self.display_name}"
        else:
            tooltip = self.display_name

        return tooltip

    def reindex_course_nav_content(self, start_module_index_at: int = 0) -> None:
        """
        Renumber the "content_index" for each node in the course navigation.
        """
        module_index = start_module_index_at
        for module_node in self.children.order_by("display_sequence").all():
            module_node.content_index = module_index
            module_node.save()
            module_index += 1
            section_index = 1
            for section_node in module_node.children.order_by("display_sequence").all():
                section_node.content_index = section_index
                section_node.save()
                section_index += 1
                unit_index = 1
                for unit_node in section_node.children.order_by("display_sequence").all():
                    unit_node.content_index = unit_index
                    unit_node.save()
                    unit_index += 1

    def clear_course_nav_content_index(self) -> None:
        """
        Clear indexing in course navigation.
        """
        for module_node in self.children.all():
            module_node.content_index = None
            module_node.save()
            for section_node in module_node.children.all():
                section_node.content_index = None
                section_node.save()
                for unit_node in section_node.children.all():
                    unit_node.content_index = None
                    unit_node.save()

    def __str__(self) -> str:
        return f"{self.id} : {self.display_name} "


class Course(Trackable):
    """
    Contains top-level information about a course.
    Does not contain actual course structure, but rather
    points to a CourseNode tree.

    """

    class Meta:
        unique_together = (("slug", "run"),)

    course_root_node = models.OneToOneField(
        CourseNode,
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name="course",
    )

    catalog_description = models.OneToOneField(
        CourseCatalogDescription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course",
    )

    slug = models.SlugField(
        max_length=200,
        null=False,
        blank=False,
        allow_unicode=True,
        help_text=_(
            "A slug for this course. Try to use only alphanumeric characters, "
            "dashes and underscores. A recommended "
            "convention is to use all caps to represent the course title "
            '(e.g. PYSJ for "Planning Your Scientific '
            'Journey") This slug plus the "run" property are used to  '
            'create a unique "token" for this course.'
        ),
    )

    run = models.CharField(
        max_length=200,
        null=False,
        blank=False,
        default="1",
        help_text=_(
            'The run for this course (e.g. "R1" to indicate the first of '
            'many runs, or "SP" for a continuously run, self-paced course). '
            'This run plus the "slug" property are used to create a '
            'unique "token" for this course.'
        ),
    )

    tags = TaggableManager(
        blank=True,
        help_text=_("Tags for this course"),
    )

    display_name = models.CharField(
        max_length=400,
        null=True,
        blank=True,
        help_text=_("The full name for the course."),
    )

    short_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_("A short name for the course. (You can leave this empty if the full name isn't that long.)"),
    )

    start_date = DateTimeField(null=True, blank=True, help_text=_("Start date for the course, if any"))

    end_date = DateTimeField(null=True, blank=True, help_text=_("End date for the course, if any"))

    # if advertised_start_date is defined, make sure it stays in sync with start_date.
    advertised_start_date = TextField(null=True, blank=True, help_text=_("A more readable version of start_date."))

    enrollment_start_date = DateTimeField(
        null=True,
        blank=True,
        help_text=_("Start date for enrollment in course, if any. " "If left blank, enrollment is assumed to be open."),
    )

    enrollment_end_date = DateTimeField(null=True, blank=True, help_text=_("End date for enrollment in course, if any"))

    # If self_paced is False, this is an 'instructor-led' course.
    self_paced = models.BooleanField(
        default=True,
        blank=False,
        null=False,
        help_text=_("Whether or not this course is self-paced."),
    )

    days_early_for_beta = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("The number of days early before the official start date that " "beta-testers can begin."),
    )

    enable_certificates = models.BooleanField(
        default=True,
        null=False,
        blank=False,
        help_text=_("Enable certificates for this course " "if any 'passing' milestones are defined."),
    )

    enable_badges = models.BooleanField(
        default=False,
        help_text=_("Enable badges for this course if any BadgeClasses " "are defined."),
    )

    enable_email_automations = models.BooleanField(
        default=False, help_text=_("Enable email automations for this course.")
    )

    enable_forum = models.BooleanField(default=False, help_text=_("Enable the forum service for this course."))

    enable_surveys = models.BooleanField(default=True, help_text=_("Enable surveys if any appear in this course."))

    playlist_url = models.URLField(
        null=True,
        blank=True,
        help_text=_("The URL to an external playlist of " "videos, if one exists (e.g. YouTube)"),
    )

    admin_only_enrollment = models.BooleanField(
        null=False,
        blank=False,
        default=False,
        help_text=_("Only staff and superusers can enroll " "students in this course"),
    )

    enable_enrollment_survey = models.BooleanField(
        null=False,
        blank=False,
        default=True,
        help_text=_("Enable enrollment 'survey' composed of " "enrollment questions if any are defined."),
    )

    # This is the introductory course content for enrolled students, shown in the 'home' tab in the course navigation.
    # (Don't confuse with general public-focused content shown on the course's catalog home page.)
    course_home_html_content = models.TextField(
        null=True,
        blank=True,
        help_text=_("HTML content for the course home for enrolled students."),
    )

    enable_course_outline = models.BooleanField(default=True, help_text=_("Enable the course outline for this course."))

    content_license = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_("The license for the course content."),
    )

    content_license_url = models.URLField(
        null=True,
        blank=True,
        help_text=_("The URL for the license for the course content."),
    )

    # DMcQ: Created our own manager so that we can use 'natural' key of slug and run
    # This is helpful in, e.g. linking fixtures by slug and run and not id.
    objects = CourseManager()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Model "property" methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @property
    def overview(self) -> str:
        """
        Get the description for this course.
        """
        if self.catalog_description:
            return self.catalog_description.overview
        return ""

    @property
    def course_group_name(self):
        """
        The name for the Django Group corresponding to this course.
        """
        return f"COURSE_GROUP_{self.token}"

    @property
    def token(self):
        """
        A course token is a unique identifier for a course, composed of the slug and the run.
        It should be a slug as well, so it can be used in URLS.
        :return:
        """
        return f"{self.slug}_{self.run}"

    @property
    def course_url(self):
        return resolve_url("course:course_page", course_slug=self.slug, course_run=self.run)

    @property
    def active_students(self) -> QuerySet:
        students = User.objects.filter(enrollments__course=self, enrollments__active=True).order_by("username")
        return students

    @property
    def enrollment_has_started(self) -> bool:
        if self.enrollment_start_date is None:
            return True
        # Compare UTC times
        return now() >= self.enrollment_start_date

    @property
    def course_has_started(self) -> bool:
        if self.start_date is None:
            return True
        # Compare UTC times
        return now() >= self.start_date

    @property
    def has_started(self) -> bool:
        if self.start_date is None:
            return True
        # Compare UTC times
        return now() >= self.start_date

    @property
    def has_discussion_group(self) -> bool:
        forum_category = getattr(self, "forum_category", None)
        return forum_category is not None

    @property
    def has_sits(self) -> bool:
        sits_exist = Block.objects.filter(
            unit_blocks__course_unit__course=self,
            type=BlockType.SIMPLE_INTERACTIVE_TOOL.name,
        ).exists()
        return sits_exist

    @property
    def count_assessments(self) -> int:
        """
        Count the number of assessments in a Course.

        Returns:
            Count of Assessment blocks in Course
        """

        def count_in_node(node: CourseNode, curr_count: int) -> int:
            if node.type == NodeType.UNIT.name:
                for sub_block in node.unit.contents.all():
                    if sub_block.type == BlockType.ASSESSMENT.name:
                        curr_count += 1
            elif node.children:
                for child_node in node.children.all():
                    curr_count = count_in_node(child_node, curr_count)
            return curr_count

        assessment_count = count_in_node(self.course_root_node, 0)
        return assessment_count

    @property
    def num_enrolled(self) -> int:
        return self.enrollments.count()

    @property
    def has_finished(self) -> bool:
        if self.end_date:
            course_is_finished = now() > self.end_date
            return course_is_finished
        return False

    @property
    def learning_objectives(self) -> Optional[List]:
        learning_objectives = get_learning_objectives_for_course(self)
        return learning_objectives

    @property
    def summary_icon(self) -> Optional[str]:
        """
        Show an icon for summary if one is defined for the course.
        Return a Bootstrap icon definition like 'bi bi-map', to be included
        in an <i/> tag.
        """

        # TODO: Move to database

        return "bi bi-map-fill"

    @property
    def simple_interactive_tool_templates(self) -> List:
        """
        A list of all SimpleInteractiveToolTemplates used in this course.
        (This is a convenience function that primarily helps with course serialization)
        """
        sit_templates = set()
        # There must be a better way than walking the whole course node tree
        for course_unit in CourseUnit.objects.filter(course=self).all():
            for block in course_unit.contents.all():
                if block.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
                    if block.simple_interactive_tool.template:
                        sit_templates.add(block.simple_interactive_tool.template)
        return list(sit_templates)

    @property
    def active_educator_resources(self) -> Optional[QuerySet]:
        return self.educator_resources.filter(enabled=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Model methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def add_to_cohort(self, user: User, cohort: "Cohort" = None) -> "CohortMembership":
        """
        Add a student to a cohort.
        IMPORTANT: If a user already exists in a cohort and that cohort
        is different from the cohort argument, the student should be moved
        into the cohort defined by the argument.

        Args:
            user:
            cohort:     Cohort to add student to. If not defined add to DEFAULT cohort
                        for this course.

        Returns:
            A CohortMembership instance representing the student's membership in a cohort.
        """

        if not user:
            logger.error("add_to_cohort() was called with user argument set to None")
            raise ValueError("user cannot be None")

        if cohort:
            if cohort.course.id != self.id:
                raise ValueError(
                    f"Cannot add user to a cohort {cohort} as that cohort is for"
                    f"a different course: {cohort.course}."
                )
        else:
            cohort = self.get_default_cohort()

        # Add student to new cohort...
        cohort_membership, membership_created = CohortMembership.objects.get_or_create(cohort=cohort, student=user)
        if membership_created:
            logger.info(f"Course : add_to_cohort() adding user {user} to cohort {cohort}")

        # Remove student from any old cohorts in this course, if necessary...
        # ( There should only be one CohortMembership, but we have to accomodate fact data model
        # does not enforce this.)
        delete_cohort_memberships = CohortMembership.objects.filter(
            ~Q(cohort__id=cohort.id), student=user, cohort__course=self
        ).all()
        if delete_cohort_memberships:
            for delete_cohort_membership in delete_cohort_memberships:
                logger.debug(f"Remove user {user} from cohort membership: {delete_cohort_membership}")
                try:
                    # Notify external email service user is no longer in this cohort.
                    EmailAutomationNotifier.remove_tag(cohort.token, user_id=user.id)
                except Exception as e:
                    logger.exception(f"Could not set tag {cohort.token} via Notifier. Error: {e}")
                try:
                    delete_cohort_membership.delete()
                except Exception:
                    logger.exception(f"Could not delete cohort membership: {delete_cohort_membership}")

        return cohort_membership

    def remove_from_cohort(self, user: User):
        """
        Remove a student from the cohort they belong to for this course.

        Args:
            user:

        Returns:
            ( nothing )
        """
        try:
            # There should only be one for this course, but since this is an M2M join,
            # let's just delete everything we find where the cohort is in this course.
            memberships = CohortMembership.objects.filter(cohort__course=self, student=user).all()
            for membership in memberships:
                membership.delete()
                logger.debug(f"user {user} removed from cohort {membership.cohort}")
                # Remove any tags from external email service
                token = membership.cohort.token
                try:
                    # Notify external email service user is no longer in this cohort.
                    EmailAutomationNotifier.remove_tag(token, user_id=user.id)
                except Exception as e:
                    logger.exception(f"Could not set tag {token} via Notifier. Error: {e}")
        except Exception:
            logger.exception(f"remove_from_cohort() Could not remove user {user} " f"from cohort in course {self}.")

    def get_default_cohort(self) -> "kinesinlms.course.models.Cohort":  # noqa
        """
        Get the DEFAULT cohort for this course.
        (If one doesn't exist, create it first).
        """

        # TODO: Replace with Factory
        default_cohort_created = False
        try:
            default_cohort = Cohort.objects.get(course=self, type=CohortType.DEFAULT.name)
        except Cohort.DoesNotExist:
            default_cohort_created = True
            logger.info(f"Course : add_to_cohort() creating a default cohort for course {self}")
            default_cohort = Cohort.objects.create(
                course=self,
                name="Default cohort",
                slug=CohortType.DEFAULT.name,
                type=CohortType.DEFAULT.name,
            )

        if default_cohort_created:
            try:
                cohort_forum_group = CohortForumGroup.objects.get(course=self, is_default=True)
                default_cohort.cohort_forum_group = cohort_forum_group
                default_cohort.save()
            except CohortForumGroup.DoesNotExist:
                logger.warning(
                    f"Created DEFAULT cohort for course {self}. However, there is no "
                    f"FormCohortGroup to assign to this cohort."
                )

        return default_cohort

    def can_view_course_admin(self, user) -> bool:
        """
        Indicates whether user can view the course admin for this course.
        """
        if user.is_superuser or user.is_staff:
            return True
        if user.is_educator:
            allowed_course_staff_roles = [CourseStaffRole.EDUCATOR.name]
            return CourseStaff.objects.filter(user=user, course=self, role__in=allowed_course_staff_roles).exists()
        return False

    def can_view_course_admin_enrollment(self, user) -> bool:
        """
        Indicates whether user can view the course admin enrollment for this course.
        Right now we're only allowing supers and staff to amn
        """
        if user.is_superuser or user.is_staff:
            return True
        return False

    def can_view_course_admin_analytics(self, user) -> bool:
        """
        Indicates whether user can view the course admin analytics for this course.
        """
        # Update this to something more granular if you want.
        return self.can_view_course_admin(user)

    def can_view_course_admin_cohorts(self, user) -> bool:
        """
        Indicates whether user can view the course admin cohorts for this course.
        """
        # Update this to something more granular if you want.
        return self.can_view_course_admin(user)

    def can_view_course_admin_assessments(self, user) -> bool:
        """
        Indicates whether user can view the Course Admin Assessments endpoints.
        """
        # Update this to something more granular if you want.
        return self.can_view_course_admin(user)

    def can_view_course_admin_resources(self, user) -> bool:
        """
        Indicates whether user can view the course admin  for this course.
        """
        # Update this to something more granular if you want.
        return self.can_view_course_admin(user)

    def __str__(self):
        return f"Course [{self.id}] : {self.display_name}"


class Cohort(Trackable):
    """
    Separates students into groups within a course,
    so that we can :
    - segment users in analytics reports
    - vary access and features based on cohort membership
    - constrain scope of discussions in Discourse
    (In early 2023 we're only really focused on the first in this list.)
    """

    class Meta:
        unique_together = ["course", "slug"]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="cohorts")

    students = models.ManyToManyField(User, through="CohortMembership", related_name="members")

    # Note that we may want many cohorts to use the same
    # CohortForumGroup. Therefore, the foreign key relationship
    # exists in this model (rather than the other direction, or a OneToOne).
    cohort_forum_group = models.ForeignKey(
        CohortForumGroup,
        on_delete=models.SET_NULL,
        related_name="cohorts",
        null=True,
        blank=True,
        help_text=_("The forum cohort group for this cohort."),
    )

    description = models.TextField(null=True, blank=True)

    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        related_name="institution",
        null=True,
        blank=True,
    )

    tags = TaggableManager(blank=True)

    name = models.CharField(max_length=200, default=None, null=True, blank=True)

    slug = models.SlugField(null=False, default=None, max_length=200, blank=False)

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in CohortType],
        default=None,
        null=True,
        blank=True,
    )

    # MODEL PROPERTIES
    @property
    def token(self):
        """
        A token that can be used to identify the cohort,
        including an indication of what course it belongs to.
        """
        # We use id rather than slug because Discourse has a limit of
        # 20 characters for a group name, which is primarily what we use this token for.
        return f"{self.course.token}_co_{self.slug}"

    @property
    def num_students(self) -> int:
        return CohortMembership.objects.filter(cohort=self).count()

    @property
    def num_students_passed(self) -> int:
        students_in_cohort = self.students.all()  # noqa
        return CoursePassed.objects.filter(course=self.course, student__in=students_in_cohort).count()

    @property
    def is_default(self) -> bool:
        return self.type == CohortType.DEFAULT.name

    def __str__(self):
        if self.name:
            return f"{self.name} (course: {self.course})"
        return f"Cohort {self.id} (type:{self.type} course:{self.course})"


class CohortMembership(Trackable):
    """
    Assigns students enrolled in a particular course to
    a cohort for that course.
    """

    class Meta:
        unique_together = ["cohort", "student"]

    cohort = models.ForeignKey(
        Cohort,
        blank=False,
        null=False,
        related_name="cohort_memberships",
        on_delete=models.CASCADE,
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        related_name="cohort_memberships",
        on_delete=models.CASCADE,
    )


class Milestone(Trackable):
    class Meta:
        unique_together = ("course", "slug")

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="milestones")
    slug = models.SlugField(null=True, blank=True, allow_unicode=True)
    name = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in MilestoneType],
        default=None,
        null=True,
        blank=True,
    )

    count_graded_only = models.BooleanField(
        default=False,
        blank=False,
        null=False,
        help_text="This milestone only counts 'graded' items.",
    )

    # Milestones may count the number of relevant blocks completed
    count_requirement = models.IntegerField(default=0, null=False, blank=True, verbose_name="Count to reach milestone")

    # And/or they can count the total score of the relevant blocks completed.
    # Specifying non-zero values for both count_requirement and min_score_requirement means both must be met for this
    # Milestone to be considered "achieved".
    min_score_requirement = models.PositiveIntegerField(
        default=0,
        null=False,
        blank=True,
        verbose_name="Minimum total score to reach milestone",
        help_text="Please set a minimum score OR count requirement, not both.",
    )

    # Some milestones aren't required to pass. They might be for informational or motivation only
    required_to_pass = models.BooleanField(default=False, null=False, blank=False)

    badge_class = models.ForeignKey(
        BadgeClass,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="milestones",
    )

    def awards_badge(self) -> bool:
        return hasattr(self, "badge_class")

    def __str__(self):
        return self.name


class MilestoneProgress(Trackable):
    """
    Tracks student progress towards a milestone.
    """

    class Meta:
        unique_together = [["milestone", "student"]]

    achieved = models.BooleanField(default=False, null=False, blank=False)

    achieved_date = models.DateTimeField(null=True, blank=True)

    # If this MilestoneProgress is for a 'simple' Milestone where
    # we're just counting the number of required activities (e.g. assessments
    # or SIT interactions), that count happens here.
    count = models.IntegerField(default=0, verbose_name="Count of progress")

    blocks = models.ManyToManyField(Block, through="MilestoneProgressBlock")

    # Total score received by the student across all the blocks linked to this Milestone.
    total_score = models.PositiveIntegerField(default=0, null=False, blank=False)

    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.CASCADE,
        related_name="progresses",
        blank=True,
        null=False,
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="progresses",
    )

    # DMcQ: It's not normalized, but it's easier to do lookups
    # to see whether a student passed if we have a foreign key to course right here,
    # rather than relying on join with Milestone table to get course info.
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="progresses")

    # If the parent Milestone awards badges, record this
    # milestone achiever's BadgeAssertion here.
    badge_assertion = models.OneToOneField(
        BadgeAssertion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="progresses",
    )

    def add_block(self, block: Block, score: int) -> (bool, int):
        """
        Add block if it's not already in saved list.
        Mark achieved and achieved date if user achieved count
        required by parent Milestone.

        Args:
            block
            score (int)

        Returns:
            (int, bool):

        An integer for the new count and a boolean flag, True if
        user *just* achieved milestone on this item.
        """
        logger.debug(f"Milestone Progress {self} adding block {block} (current count {self.count})")
        if self.blocks.filter(id=block.id).exists():
            return self.count, False

        self.count += 1
        self.total_score += score
        just_achieved = self.mark_achieved()
        new_count = self.count

        MilestoneProgressBlock.objects.create(milestone_progress=self, block=block, score=score)

        # Update count and total_score using F statements to avoid race conditions.
        self.count = F("count") + 1
        self.total_score = F("total_score") + score
        self.save()

        return new_count, just_achieved

    def remove_block(self, block: Block) -> int:
        """
        Removes a block from the saved list and adjusts the block count and score.
        DOES NOT adjust completion. Assumes that once
        a student completes something, they don't lose it.

        :param block:
        :return: new count
        """
        logger.debug(f"Milestone Progress {self} Removing block {block}")
        delete_block = self.blocks.filter(id=block.id).first()
        if not delete_block:
            logger.warning(
                f"Milestone Progress {self}: remove_block() was called for " f"block {block} but it was not in the list"
            )
            return self.count

        score = delete_block.score
        delete_block.delete()
        new_count = self.count - 1

        # Update count and total_score using F statements to avoid race conditions.
        self.count = F("count") - 1
        self.total_score = F("total_score") - score
        self.save()
        return new_count

    def mark_achieved(self) -> bool:
        """
        Mark this MilestoneProgress as "achieved" and set the "achieved_date" if:

        * it hasn't already been "achieved", AND
        * user has achieved the count or score required by the parent Milestone

        Returns:
            True if MilestoneProgress was just achieved; False otherwise.
        """
        just_achieved = False
        if not self.achieved:
            # If we've reached the milestone requirement count...
            if self.milestone.count_requirement:
                just_achieved = bool(self.count >= self.milestone.count_requirement)
            # OR we've reached the milestone minimum score...
            elif self.milestone.min_score_requirement:
                just_achieved = bool(self.total_score >= self.milestone.min_score_requirement)

            # ...then this milestone has been achieved.
            if just_achieved:
                self.achieved = True
                self.achieved_date = now()
                logger.debug(f"Milestone Progress {self} just achieved!")

        return just_achieved

    def rescore(self, block: Optional[Block] = None) -> int:
        """
        Rescores the SubmittedAnswers associated with the current MilestoneProgress, and adjusts the
        total_score accordingly.

        The current MilestoneProgress must have type CORRECT_ANSWERS.

        Like remove_block, this method DOES NOT adjust completion.
        Assumes that once a student completes something, they don't lose it.

        Args:
            block (optional)    If provided, will only rescore SubmittedAnswers for this block: the
                                existing SubmittedAnswer's score will be used for all others.

        Returns:
            bool indicating whether this milestone was just achieved.

        """
        assert self.milestone.type == MilestoneType.CORRECT_ANSWERS.name

        progress_blocks = {
            progress_block.block_id: progress_block
            for progress_block in MilestoneProgressBlock.objects.filter(milestone_progress=self)
        }

        # Fetch the SubmittedAnswers relevant to this MilestoneProgress object.
        # (Import here to avoid circular dependency.)
        from kinesinlms.assessments.models import SubmittedAnswer

        answers = SubmittedAnswer.objects.filter(course=self.course, student=self.student)
        answers = answers.select_related("assessment", "assessment__block")
        if self.milestone.count_graded_only:
            answers = answers.filter(assessment__graded=True)

        total_score = 0
        create_progress_blocks = []
        update_progress_blocks = []
        for answer in answers:
            block_id = answer.assessment.block_id

            # Re-score this answer if it's for the requested block,
            # or if we're re-scoring all blocks.
            if not block or block_id == block.id:
                status = answer.update_status()

            # Otherwise, just use the status and score we have.
            else:
                status = answer.status

            if status in ANSWER_STATUS_FINISHED:
                if block_id in progress_blocks:
                    progress_block = progress_blocks[block_id]
                    update_progress_blocks.append(progress_block)

                else:
                    progress_block = MilestoneProgressBlock(
                        milestone_progress=self,
                        block_id=block_id,
                    )
                    create_progress_blocks.append(progress_block)

                progress_block.score = answer.score
                total_score += answer.score

        # Save changes to the MilestoneProgressBlocks in bulk
        if create_progress_blocks:
            MilestoneProgressBlock.objects.bulk_create(create_progress_blocks)
        if update_progress_blocks:
            MilestoneProgressBlock.objects.bulk_update(update_progress_blocks, fields=["score"])

        # Update our totals, and re-assess achievement.
        self.count = len(create_progress_blocks) + len(update_progress_blocks)
        self.total_score = total_score
        just_achieved = self.mark_achieved()
        self.save()

        return just_achieved

    @classmethod
    def bulk_remove_block(
        cls,
        progresses: QuerySet["MilestoneProgress"],
        block: Block,
    ) -> int:
        """
        Efficiently removes a block from the given MilestoneProgresses, and adjusts the block count and total_score.

        Like remove_block, this method DOES NOT adjust completion.
        Assumes that once a student completes something, they don't lose it.

        Args:
            progresses:      iterable list of MilestoneProgress
            block:

        Returns:
            number of updated MilestoneProgresses.
        """
        # Locate the related MilestoneProgress.blocks
        # We'll use these to decide which MilestoneProgress objects to update,
        # and how much to subtract from their total_score.
        blocks_to_delete = MilestoneProgressBlock.objects.filter(
            milestone_progress__in=progresses.all(),
            block=block,
        )
        milestone_blocks = {
            milestone_block.milestone_progress_id: milestone_block for milestone_block in blocks_to_delete
        }

        # Update the MilestoneProgress block count and total_score, in bulk.
        updated_progress = []
        for milestone_progress in progresses.all():
            progress_block = milestone_blocks.get(milestone_progress.id)
            if progress_block:
                milestone_progress.count = F("count") - 1
                milestone_progress.total_score = F("total_score") - progress_block.score
                updated_progress.append(milestone_progress)
        count = MilestoneProgress.objects.bulk_update(updated_progress, ["count", "total_score"])

        # Delete the related MilestoneProgressBlocks
        blocks_to_delete.delete()

        return count


class MilestoneProgressBlock(Trackable):
    """ ""
    Links MilestoneProgress to a learning_library Block.
    """

    milestone_progress = models.ForeignKey(MilestoneProgress, on_delete=models.CASCADE, null=False, blank=False)

    block = models.ForeignKey(Block, on_delete=models.CASCADE, null=False, blank=False)

    # Score achieved by the student for completing this block
    score = models.PositiveIntegerField(default=1, null=False, blank=True)


class CoursePassed(Trackable):
    """
    Track course completion by a student. We save a course 'completion' rather
    than dynamically deciding if a student passed a course by looking at all MilestoneProgresses.
    This should keep the model easier to understand and as well as make it easier to determine
    whether a student has passed.
    """

    class Meta:
        unique_together = (("course", "student"),)

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_passed_items")

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="course_passed_items",
    )

    badge_assertion = models.OneToOneField(
        BadgeAssertion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course_passed_items",
    )


class Enrollment(Trackable):
    """
    Manages enrollment status of students in available courses.
    """

    class Meta:
        unique_together = (("student", "course"),)

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    active = models.BooleanField(
        default=False,
        blank=False,
        null=False,
    )

    beta_tester = models.BooleanField(
        default=False,
        blank=False,
        null=False,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        course_group_name = self.course.token
        student: User = getattr(self, "student", None)
        if not student:
            # Should never get here, since student is required field
            return
        if self.active:
            # Make sure student is in course group
            try:
                group, created = Group.objects.get_or_create(name=course_group_name)
                student.groups.add(group)
            except Exception:
                logger.exception(f"Could not add {student.username} to " f"course group {course_group_name}. ")
        else:
            # Make sure student *is not* in course group
            try:
                group = Group.objects.get(name=course_group_name)
            except Group.DoesNotExist:
                group = None
            if group:
                try:
                    student.groups.remove(group)
                except Exception:
                    logger.exception(f"Could not remove {student.username} from " f"course group{course_group_name}.")

    @property
    def enrollment_survey_required_url(self) -> Optional[str]:
        """
        URL if this user needs to complete an enrollment
        survey before starting the course.
        """
        enrollment_survey = getattr(self.course, "enrollment_survey", None)
        if enrollment_survey:
            completion = EnrollmentSurveyCompletion.objects.filter(
                student=self.student, enrollment_survey=enrollment_survey
            ).exists()
            if not completion:
                enrollment_survey_url = reverse(
                    "catalog:enrollment_survey",
                    kwargs={"course_slug": self.course.slug, "course_run": self.course.run},
                )
                return enrollment_survey_url
        return False


class EnrollmentSurveyQuestionType(Enum):
    TEXT = "Text"
    MULTIPLE_CHOICE = "Multiple Choice"
    POLL = "Poll"


class EnrollmentSurveyQuestion(Trackable):
    class Meta:
        ordering = ["display_order"]

    question_type = models.CharField(
        max_length=100,
        choices=[(item.name, item.value) for item in EnrollmentSurveyQuestionType],
        blank=False,
        default=EnrollmentSurveyQuestionType.TEXT,
        null=False,
    )

    question = models.TextField(max_length=500, null=False, blank=False)

    definition = models.JSONField(null=True, blank=True)

    display_order = models.IntegerField(default=0, null=False)

    # noinspection PyTypeChecker
    def clean(self):
        if self.question_type == EnrollmentSurveyQuestionType.MULTIPLE_CHOICE.name:
            if not self.definition:
                raise ValidationError("definition must be provided if this is a MULTIPLE_CHOICE question")
            for item in self.definition:
                if "key" not in item:
                    raise ValidationError("definition item must have a 'key' key for each question option")
                if "value" not in item:
                    raise ValidationError("definition item must have a 'value' key for each question option")


class EnrollmentSurveyAnswer(Trackable):
    # Answer is linked to student via Enrollment
    # However we need to create this instance before we can get
    # an enrollment instance, so don't require it.
    enrollment = models.ForeignKey(
        Enrollment,
        null=True,
        blank=True,
        related_name="enrollment_questions",
        on_delete=models.CASCADE,
    )

    enrollment_question = models.ForeignKey(
        EnrollmentSurveyQuestion,
        related_name="answers",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )

    answer = models.TextField(max_length=500, null=False, blank=False)


class EnrollmentSurvey(Trackable):
    course = models.OneToOneField(Course, null=False, related_name="enrollment_survey", on_delete=models.CASCADE)

    questions = models.ManyToManyField(EnrollmentSurveyQuestion, related_name="enrollment_surveys")

    enabled = models.BooleanField(default=True, null=False)


class EnrollmentSurveyCompletion(Trackable):
    """
    An entry in this join table signifies a completion of the
    questions in an enrollment survey.
    """

    class Meta:
        unique_together = ("enrollment_survey", "student")

    enrollment_survey = models.ForeignKey(
        EnrollmentSurvey,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="enrollment_survey_completion",
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="enrollment_survey_completion",
    )


class Bookmark(RepresentationMixin, Trackable):
    """
    Simple way of allowing students to bookmark units.
    As in other models, we link to both a discreet unit node
    and directly to the encompassing course,
    to provide more convenient ways of bookmark lookups.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    # We link to UnitNode rather than CourseUnit as student
    # bookmarks an exact location in the course. Although
    # unlikely, a CourseUnit can appear in multiple places
    # in a course, so we don't want to link to that.
    unit_node = models.ForeignKey(
        CourseNode,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    # Not normalized, but helpful when building view!
    course = models.ForeignKey(
        Course,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    def to_react_representation(self, context=None):
        obj = {"course_id": self.course.id, "unit_node_id": self.unit_node.id}
        return obj

    def clean(self):
        # Leaf nodes should be "unit" blocks
        if self.unit_node.type is not NodeType.UNIT.name:
            raise ValidationError("Only 'unit' nodes can be assigned to a bookmark")


class NoticeType(Enum):
    IMPORTANT_DATE = "Important date"
    NEWS_ITEM = "News Item"

    def __str__(self):
        return self.name


class CourseResource(Trackable):
    """
    Resources specific to this course, and relevant for the whole course,
    not a particular block.

    These are typically shown on course home page and provide a link to something
    like a syllabus, etc.

    These are not meant to be linked to a Block. The Resource model is used for that.
    My guess is a "course" resource is fundamentally different from a Resource that
    can be linked to blocks (and these concepts will diverge more).
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=False, blank=False)

    course = models.ForeignKey(
        Course,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="course_resources",
        help_text=_("A resource (e.g. PDF file) for this course."),
    )

    name = models.CharField(
        max_length=200,
        null=False,
        blank=False,
        help_text=_("The name of the resource."),
    )

    description = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text=_("A short description of the resource."),
    )

    resource_file = models.FileField(
        upload_to="course_resources/",
        null=True,
        blank=True,
    )


class Notice(Trackable):
    """
    Notices for a course. These are typically
    shown on course home page and announce date-sensitive
    news items.
    """

    class Meta:
        order_with_respect_to = "sequence"

    course = models.ForeignKey(
        Course,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="notices",
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in NoticeType],
        default=None,
        null=True,
        blank=True,
    )

    title = models.CharField(null=True, blank=True, max_length=300)

    html_content = models.TextField(null=True, blank=True)

    date = models.DateTimeField(null=True, blank=True)

    resource_url = models.CharField(null=True, blank=True, max_length=500)

    sequence = models.IntegerField(null=False, blank=False, default=0)

    def clean(self):
        if self.type == NoticeType.IMPORTANT_DATE.name:
            if not self.date:
                raise ValidationError("Must provide date for Important Date")
        elif self.type == NoticeType.NEWS_ITEM.name:
            if not self.html_content:
                raise ValidationError("Must provide html content for News Item")


class CourseStaffRole(Enum):
    EDUCATOR = "Educator"
    # ... more to come? ...


class CourseStaff(Trackable):
    """
    CourseStaff are users who have been
    designated to have special roles for a particular course.

    This join table allows us to give users special permissions and
    other settings on an individual Course object level, while not having to
    give the user the 'is_staff' setting or monkey around with django-guardian
    or multiple groups for courses (basic group, then educators group).
    """

    course = models.ForeignKey(
        "Course",
        related_name="course_staffs",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        related_name="course_staffs",
        on_delete=models.CASCADE,
    )

    role = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in CourseStaffRole],
        default=CourseStaffRole.EDUCATOR.name,
        null=True,
        blank=True,
    )

    allow_all_cohorts = models.BooleanField(
        "Allow this course staff member to view all cohorts",
        default=False,
        null=False,
        blank=False,
    )

    # A CourseStaff user can be responsible for more than one cohort.
    # These relationships are ignored, however, if allow_all_cohorts is True.
    cohorts = models.ManyToManyField(Cohort, blank=True)

    def clean(self):
        user = getattr(self, "user", None)
        if user and (self.role == CourseStaffRole.EDUCATOR.name and user.is_educator is False):
            raise ValidationError(
                f"A user must be in the 'educator' group before being assigned as course staff "
                f"for any particular course ({self.course})."
            )

    def can_access_cohort(self, cohort: Cohort):
        """
        Can this CourseStaff user access a cohort in this course?
        """
        if not cohort:
            return False
        all_cohorts_in_course = self.course.cohorts
        if not all_cohorts_in_course.filter(id=cohort.id).exists():
            # Wasn't even in this course.
            return False
        if self.allow_all_cohorts:
            return True
        return self.cohorts.filter(id=cohort.id).exists()
