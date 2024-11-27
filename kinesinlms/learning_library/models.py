import logging
import os
import uuid
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _
from django_react_templatetags.mixins import RepresentationMixin
from jsonschema import validate
from taggit.managers import TaggableManager

from kinesinlms.core.models import Trackable
from kinesinlms.core.utils import truncate_string
from kinesinlms.forum.models import ForumCategory, ForumSubcategory, ForumTopic
from kinesinlms.learning_library.constants import (
    BlockStatus,
    BlockType,
    ContentFormatType,
    LibraryItemType,
    ResourceType,
    VideoPlayerType,
)
from kinesinlms.learning_library.schema import (
    ANSWER_LIST_BLOCK_SCHEMA,
    CALLOUT_BLOCK_SCHEMA,
    HTML_CONTENT_BLOCK_SCHEMA,
    SIMPLE_INTERACTIVE_TOOL_BLOCK_SCHEMA,
    SURVEY_BLOCK_SCHEMA,
    VIDEO_BLOCK_SCHEMA,
)
from kinesinlms.sits.constants import SimpleInteractiveToolType

logger = logging.getLogger(__name__)


class Resource(Trackable):
    """
    A global, immutable resource that can be used by blocks.
    This is mainly images, PDFs, text files and other types of
    non-HTML files that can be used by blocks.
    """

    uuid = models.UUIDField(
        primary_key=False,
        default=uuid.uuid4,
        unique=True,
        null=False,
        blank=True,
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in ResourceType],
        default=ResourceType.IMAGE.name,
        null=False,
        blank=False,
    )

    resource_file = models.FileField(upload_to="block_resources")

    name = models.CharField(
        max_length=400,
        null=True,
        blank=True,
        help_text=_(
            "A name for this resource. This name is used in the admin "
            "interface and in the learning library."
        ),
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "A short description of the resource. If this is an image, the "
            "description will be used as the alt text."
        ),
    )

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.file_name})"
        return f"Resource [{self.id}] : {self.file_name}"

    @property
    def info(self) -> Dict:
        return {
            "type": self.type,
            "filename": self.file_name,
        }

    @property
    def url(self) -> Optional[str]:
        if self.resource_file:
            return self.resource_file.url
        else:
            return None

    @property
    def file_name(self) -> Optional[str]:
        if self.resource_file:
            return os.path.basename(self.resource_file.name)
        else:
            return None

    @property
    def extension(self):
        try:
            name, extension = os.path.splitext(self.resource_file.name)
            return extension
        except Exception:
            logger.warning("Could not get Resource extention ")
            return ""

    @property
    def as_html(self) -> Optional[str]:
        """
        Convenience method
        """
        if self.type != ResourceType.IMAGE.name:
            raise Exception(f"Resource type {self.type} is not supported for as_html()")

        if not self.resource_file:
            return ""

        html = f"<img src='{self.resource_file.url}' class='img' alt='{self.description}' />"

        return html


class UnitBlock(Trackable):
    """ ""
    Arranges blocks into a unit. We don't need an MPTT because
    this grouping is more basic, won't change often, isn't involved in navigation
    and therefore has no need of MPTT functions like next, prev, etc.
    """

    class Meta:
        ordering = ["block_order"]

    course_unit = models.ForeignKey(
        "course.CourseUnit",
        on_delete=models.CASCADE,
        related_name="unit_blocks",
        null=False,
        blank=False,
        db_index=True,
    )

    block = models.ForeignKey(
        "Block",
        on_delete=models.CASCADE,
        related_name="unit_blocks",
        null=False,
        blank=False,
        db_index=True,
    )

    slug = models.SlugField(
        unique=True,
        max_length=200,
        null=True,
        blank=True,
        allow_unicode=True,
        help_text=_("A slug to represent this block " "in this particular unit."),
    )

    label = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_(
            "A label that should appear next to this "
            "block when rendered in this particular unit."
        ),
    )

    # This allows us to number assessments on a unit like 1, 2, 3
    # without having to bake that number into a block or assessment instance.
    # This is different from just label as it's dedicated to local numbering
    # certain blocks (like assessments or activities) on a unit page.
    index_label = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_(
            "An index number that should appear next to this "
            "block when rendered in this particular unit."
        ),
    )

    block_order = models.PositiveIntegerField(default=0)

    # Hide a block within a CourseUnit
    hide = models.BooleanField(
        default=False,
        blank=False,
        null=False,
        help_text=_("Hide this block in in this particular unit."),
    )

    # If the referenced block is interactive, this field
    # can turn that interactivity off for a particular unit.
    read_only = models.BooleanField(
        default=False,
        blank=False,
        null=False,
        help_text=_("This block is read only in this particular unit."),
    )

    # This is a new way of grouping items into a summary view (like "My Responses" or "Printable Review")
    # at the end of a course. Courses pre Aug 2022 will have to be updated.
    include_in_summary = models.BooleanField(
        default=False,
        blank=False,
        null=False,
        help_text=_(
            "This block is included in any course summary pages (like "
            "'My Responses' or 'Printable Review'."
        ),
    )

    def __str__(self):
        s = f"UnitBlock [{self.id}]"
        if self.slug:
            return f"{s} : {self.slug}"
        else:
            return s


class Block(RepresentationMixin, Trackable):
    """
    A Block encapsulates some form of content meant to be used in a course or
    as stand-alone content in the Learning Library and thereby available
    to be placed in a pathway.

    Detailed information for more complex block types should use composition to
    hold a ref to a block and thereby be kept in a separate table. For example,
        -   assessment details are stored in a related Assessment model
        -  'simple interactive tools' like diagrams or 'tabletools'
            are store in a related SimpleInteractiveTool model.

    ...while simple blocks like HTML_CONTENT or VIDEO block types can
    just store their info here in html_content and/or json_content.

    For example, "VIDEO" block types should be able to appear in more than one unit.
    That way they can be used in different courses but only updated in one place.

    However, some block types, like "ASSESSMENT," can only appear in one unit.

    """

    class Meta:
        indexes = [GinIndex(fields=["search_vector"])]

    tags = TaggableManager(blank=True)

    uuid = models.UUIDField(primary_key=False, default=uuid.uuid4, editable=False)

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in BlockType],
        default=BlockType.HTML_CONTENT.name,
        null=False,
        blank=False,
    )

    display_name = models.CharField(
        max_length=400,
        null=True,
        blank=True,
        help_text=_(
            "A text header to be shown at the top of the block. "
            "(Only some block types display this field.)"
        ),
    )

    hide_display_name = models.BooleanField(
        default=False,
        help_text=_("Always hide this block's display name."),
    )

    short_description = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "A short description of the unit to be used when listing blocks "
            "outside of course or for staff composing a course. This "
            "description is not usually shown in an actual course unit."
        ),
    )

    slug = models.SlugField(
        max_length=200,
        null=True,
        blank=True,
        allow_unicode=True,
        unique=False,
        help_text=_(
            "A slug for this block.The main use of a slug here is "
            "simple indication of purpose of block, both for students "
            "(when seen in a URL for this block if its available in the learning "
            "library) and for admins (when viewing event data in "
            "event objects)."
        ),
    )

    course_only = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        help_text=_(
            "Set this flag to tru to prevent this block from "
            "appearing anywhere outside of the courses it appears in. "
            "(i.e. don't allow to appear as item in learning library)"
        ),
    )

    enable_template_tags = models.BooleanField(
        default=True,
        null=False,
        blank=True,
        help_text=_(
            "Enables a limited number of template tags in "
            "this model's html_content field."
        ),
    )

    # HTML content for this block. When defined, it's usually
    # just rendered into a template.
    html_content = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "HTML content for this block. For most blocks, when this field "
            "is defined, the contents are just rendered into a template when "
            "a unit page is constructed for a student."
        ),
    )

    # Format type of html_content. This is used to determine how to render
    # the html_content field.
    html_content_type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in ContentFormatType],
        default=ContentFormatType.HTML.name,
        null=False,
        blank=False,
    )

    # JSON content for this block. This holds different data depending
    # on the block type. We define JSON schemas to validate incoming
    # data and really just help us remember the shape of the data for
    # a particular Block type.
    # Block template renderers or React-based components should
    # also expect this data to be in the proper shape for the Block type.
    json_content = JSONField(
        null=True,
        blank=True,
        help_text=_(
            "JSON content for this block. This holds different "
            "data depending on the block type."
        ),
    )

    # Status for this block. At the moment that just means 'draft' or
    # 'published', so this field is a way of staging content for the library.
    status = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in BlockStatus],
        default=BlockStatus.PUBLISHED.name,
        null=False,
        blank=False,
    )

    # Do we even need version? We're not going to save history.
    # Maybe just to help author / user understand changes.
    version = models.IntegerField(default=0)

    # SEARCH FIELDS
    # For text search...
    search_vector = SearchVectorField(null=True, editable=False)

    # These are the validators to check a particular type's
    # json_content field. (Each block type can store its own
    # shape of data in json_content.)
    # NOTE: Every type that uses this field should have a
    #       validator defined here!
    json_content_validators = {
        BlockType.SURVEY.name: SURVEY_BLOCK_SCHEMA,
        BlockType.HTML_CONTENT.name: HTML_CONTENT_BLOCK_SCHEMA,
        BlockType.VIDEO.name: VIDEO_BLOCK_SCHEMA,
        BlockType.CALLOUT.name: CALLOUT_BLOCK_SCHEMA,
        BlockType.ASSESSMENT.name: None,
        BlockType.ANSWER_LIST.name: ANSWER_LIST_BLOCK_SCHEMA,
        BlockType.SIMPLE_INTERACTIVE_TOOL.name: SIMPLE_INTERACTIVE_TOOL_BLOCK_SCHEMA,
    }

    resources = models.ManyToManyField(Resource, through="BlockResource")

    # ~~~~~~~~~~~~~~~~~~~~~~~~
    # MODEL METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~

    def clean(self):
        """
        Before saving, Make sure JSON fields have correct structure
        """
        logger.debug(f"Clean() block model instance : {self}")
        if self.json_content:
            try:
                validator_schema = self.json_content_validators.get(self.type)
                if validator_schema:
                    validate(self.json_content, validator_schema)
                else:
                    logger.info(f"No validator defined for block type {self.type}")
            except KeyError:
                raise ValidationError(
                    "No validator schema defined for this "
                    "type but json content exists"
                )
            except Exception:
                raise ValidationError("Invalid JSON")

        if not self.slug:
            self.slug = self.uuid

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            logger.warning(
                f"Could not save slug for Block {self.display_name} using slug {self.slug} "
            )
            logger.warning(f"Saving with slug set to uuid : {self.uuid}")
            self.slug = self.uuid
            super().save(*args, **kwargs)

    def to_react_representation(self, context=None) -> Dict:
        """
        Build up a JSON object to be passed to the React
        component embedded in the unit page.

        Include data and metadata needed by target
        component so it can render and operate.
        """

        course = context.get("course", None)
        if course:
            course_slug = course.slug
            course_run = course.run
        else:
            course_slug = None
            course_run = None

        course_unit = context.get("course_unit", None)
        if course_unit:
            course_unit_id = course_unit.id
            course_unit_slug = course_unit.slug
        else:
            course_unit_id = None
            course_unit_slug = None

        unit_node_slug = context.get("unit_node_slug", None)
        cohort = context.get("cohort", None)

        # Add basic context info all library components need...

        obj = {
            "course_run": course_run,
            "course_slug": course_slug,
            "unit_node_slug": unit_node_slug,
            "course_unit_id": course_unit_id,
            "course_unit_slug": course_unit_slug,
            "block_id": self.id,
            "block_uuid": self.uuid,
            "django_pipeline": settings.DJANGO_PIPELINE,
        }

        if self.type == BlockType.VIDEO.name:
            # As a habit, don't just send json_content. Only
            # pull out info that's required by front end.
            obj["video_id"] = self.json_content["video_id"]

        elif self.type == BlockType.FORUM_TOPIC.name:
            """
            Note that this code presumes all Discourse Topics linked to via
            a "ForumTopic" block are cohort-based topics.
            In the future we may want to reverse the Block / ForumTopic relationship
            so it's 1) easier to get the ForumTopic here and 2) easier to link
            multiple Blocks to one ForumTopic (perhaps that same topic appears a couple
            times during a course).
            """
            try:
                if not cohort:
                    raise Exception("Cannot get topic because cohort is not in context")
                forum_category = ForumCategory.objects.get(course=course)
                forum_subcategory = ForumSubcategory.objects.get(
                    cohort_forum_group=cohort.cohort_forum_group,
                    forum_category=forum_category,
                )
                disc_topic = ForumTopic.objects.get(
                    forum_subcategory=forum_subcategory, block=self
                )
                topic_id = disc_topic.topic_id
                topic_slug = disc_topic.topic_slug
            except Exception:
                logger.exception("Could not load ForumTopic")
                topic_id = None
                topic_slug = None
            obj["topicID"] = topic_id
            obj["topicSlug"] = topic_slug
        elif self.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
            if hasattr(self, "simple_interactive_tool"):
                simple_interactive_tool = self.simple_interactive_tool
                sit_obj = simple_interactive_tool.to_react_representation(context)
                obj.update(sit_obj)
            else:
                logger.error(
                    "Cannot find simple_interactive_tool row for "
                    "block with SIMPLE_INTERACTIVE_TOOL type."
                )

        return obj

    @property
    def export_title(self) -> str:
        """
        Return a name for this block that is suitable for export.
        Used when no display_name is set.
        """
        return f"{self.type} block uuid {self.uuid}"

    @property
    def summary_text(self) -> str:
        """
        Provide a short summary of the content in this block.
        Useful for QuickNav and other places where a summary of
        less than 60 or so characters is needed.
        """

        # Default text...should be replaced below.
        summary = f"Block {self.id}"

        # If short_description is defined, always return that...
        if self.short_description:
            summary = self.short_description

        elif self.type == BlockType.HTML_CONTENT.name:
            soup = BeautifulSoup(self.html_content)
            summary = soup.get_text()

        elif self.type == BlockType.VIDEO.name:
            header = self.json_content.get("header", None)
            if self.display_name:
                summary = self.display_name
            elif header:
                summary = header
            else:
                summary = f"Video: {self.slug}"

        elif self.type == BlockType.ASSESSMENT.name:
            if self.assessment.question:
                soup = BeautifulSoup(self.assessment.question)
                summary = soup.get_text()
                summary = f"Assessment: {summary}"

            elif self.display_name:
                summary = f"Assessment: {self.display_name}"

            else:
                summary = f"Assessment: {self.slug}"

        elif self.type == BlockType.FORUM_TOPIC.name:
            if self.display_name:
                summary = f"Discuss: {self.display_name}"
            else:
                summary = f"Discuss: {self.slug}"

        elif self.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
            sit_name = SimpleInteractiveToolType[
                self.simple_interactive_tool.tool_type
            ].value

            if self.display_name:
                summary = f"{sit_name} Activity: {self.display_name}"
            else:
                summary = f"{sit_name} Activity: {self.slug}"

        summary = truncate_string(summary, 70)
        return summary

    @property
    def helper_javascript_libraries(self) -> List[str]:
        """
        Return any 'helper' javascript libraries required by this block.
        Right now that just means looking to see if this block has a
        SimpleInteractiveTool.
        """
        helper_libraries = []
        if self.simple_interactive_tool is not None:
            helper_libraries = self.simple_interactive_tool.helper_javascript_libraries
        return helper_libraries

    @property
    def type_display_name(self) -> str:
        if self.type:
            block_type = BlockType[self.type].value
            return block_type
        else:
            return ""

    @property
    def assessment_type_display_name(self) -> str:
        if hasattr(self, "assessment"):
            return self.assessment.type
        else:
            return ""

    @property
    def launch_type(self) -> str:
        # TODO: sytem for specifying launch type
        return "new_window"
        # return "iframe"

    def __str__(self):
        return "{} :  type : {}  display_name : {} ".format(
            self.id, self.type, self.display_name
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # TYPE-SPECIFIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # TODO: Abstract this type-specific logic and make approach more elegant.

    @property
    def video_id(self) -> Optional[str]:
        """Convenience method"""
        if self.type == BlockType.VIDEO.name:
            data = getattr(self, "json_content", None)
            if not data:
                return None
            try:
                video_id = self.json_content.get("video_id", None)
                return video_id
            except Exception:
                logger.exception("Video block didn't have video_id in json_content")
        return None

    @property
    def video_header(self) -> Optional[str]:
        """Convenience method"""
        if self.type == BlockType.VIDEO.name:
            data = getattr(self, "json_content", None)
            if not data:
                return None
            try:
                video_name = self.json_content.get("header", None)
                return video_name
            except Exception:
                logger.exception("Video block didn't have header in json_content")
        return None

    @property
    def thumbnail_url(self):
        if self.type == BlockType.VIDEO.name:
            data = getattr(self, "json_content", None)
            if not data:
                return None
            player_type = self.json_content.get(
                "player_type", VideoPlayerType.YOUTUBE.name
            )
            video_id = self.json_content.get("video_id", None)
            if not video_id:
                logger.error(
                    f"thumbnail_url(): 'VIDEO' type block id {self.id} does not have a video_id property. "
                )
                return None
            if player_type == VideoPlayerType.YOUTUBE.name:
                url = f"https://img.youtube.com/vi/{video_id}/default.jpg"
                return url
        else:
            # unsupported
            return None

    @property
    def discussion_topic_title(self):
        return self.display_name


class LibraryItem(Trackable):
    """
    Blocks or CourseUnits that should be shown in the learning library,
    and by extension be available for inclusion in 'pathways.'
    """

    course_unit = models.ForeignKey(
        "course.CourseUnit",
        on_delete=models.CASCADE,
        related_name="library_item",
        null=True,
        blank=True,
    )

    block = models.ForeignKey(
        "learning_library.Block",
        on_delete=models.CASCADE,
        related_name="library_item",
        null=True,
        blank=True,
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in LibraryItemType],
        default=LibraryItemType.BLOCK.name,
        null=False,
        blank=False,
    )

    tags = TaggableManager(blank=True)

    # HTML content for this library item to provide extra information
    # or context in library pages. When defined, it's usually just
    # rendered into a template.
    html_content = models.TextField(null=True, blank=True)

    hidden = models.BooleanField(default=False, null=False, blank=True)

    # This library item can be used in pathways
    allow_pathway = models.BooleanField(default=True, null=False, blank=True)

    def clean(self):
        super().clean()
        if not self.course_unit and not self.block:
            raise ValidationError("Either course_unit or block must be defined.")
        if self.course_unit and self.block:
            raise ValidationError(
                "Only one of course_unit or block can be defined, not both."
            )

    @property
    def uuid(self):
        if self.type == LibraryItemType.BLOCK.name:
            return self.block.uuid
        elif self.type == LibraryItemType.UNIT.name:
            return self.course_unit.uuid


class BlockLearningObjective(models.Model):
    learning_objective = models.ForeignKey(
        "learning_library.LearningObjective",
        on_delete=models.CASCADE,
        related_name="block_learning_objectives",
        null=False,
        blank=False,
    )

    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name="block_learning_objectives",
        null=False,
        blank=False,
    )

    display_in_course = models.BooleanField(default=True, null=False, blank=False)

    display_in_learning_library = models.BooleanField(
        default=True, null=False, blank=False
    )


class LearningObjective(models.Model):
    slug = models.SlugField(
        max_length=200, unique=True, null=False, blank=False, allow_unicode=True
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in LibraryItemType],
        default=LibraryItemType.BLOCK.name,
        null=False,
        blank=False,
    )

    tags = TaggableManager(blank=True)

    description = models.TextField(null=True, blank=True)

    blocks = models.ManyToManyField(
        Block, through=BlockLearningObjective, related_name="learning_objectives"
    )


class BlockResource(Trackable):
    """
    Links a global, immutable resource to a block.
    """

    class Meta:
        unique_together = ("block", "resource")

    block = models.ForeignKey(
        Block, null=False, related_name="block_resources", on_delete=models.CASCADE
    )

    resource = models.ForeignKey(
        Resource, null=False, related_name="block_resources", on_delete=models.CASCADE
    )

    @property
    def description(self) -> Optional[str]:
        """
        Convenience method
        """
        if self.resource:
            return self.resource.description
        else:
            return None

    @property
    def file_name(self) -> Optional[str]:
        """
        Convenience method
        """
        if self.resource:
            return self.resource.file_name
        else:
            return None

    @property
    def extension(self) -> Optional[str]:
        """
        Convenience method
        """
        if self.resource:
            return self.resource.extension
        else:
            return None

    def clean(self):
        super().clean()
        if self.resource.type == ResourceType.JUPYTER_NOTEBOOK.name:
            existing = BlockResource.objects.filter(
                block=self.block, resource__type=ResourceType.JUPYTER_NOTEBOOK.name
            ).exclude(id=self.id)
            if existing.exists():
                filename = existing.first().resource.file_name
                raise ValidationError(
                    f"A Block can only have one Jupyter notebook resource. "
                    f"This block already has notebook: {filename}"
                )
