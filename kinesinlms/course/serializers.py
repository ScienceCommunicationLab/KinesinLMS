import logging
import re
import uuid
from collections import OrderedDict
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional

import pytz
import requests
from django.core.files import File
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import SlugRelatedField
from taggit.serializers import TaggitSerializer, TagListSerializerField

from kinesinlms.badges.models import BadgeClass
from kinesinlms.badges.serializers import BadgeClassSerializer
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.catalog.serializers import CourseCatalogDescriptionSerializer
from kinesinlms.certificates.models import Signatory
from kinesinlms.certificates.serializers import (
    CertificateTemplateSerializer,
    SignatorySerializer,
)
from kinesinlms.certificates.service import CertificateTemplateFactory
from kinesinlms.composer.import_export.kinesinlms.constants import (
    ImportCopyType,
)
from kinesinlms.composer.models import CourseMetaConfig
from kinesinlms.core.serializers.serializer_fields import SanitizedHTMLField
from kinesinlms.course.constants import CourseUnitType
from kinesinlms.course.factory import CourseFactory
from kinesinlms.course.models import (
    Bookmark,
    Cohort,
    CohortType,
    Course,
    CourseNode,
    CourseResource,
    CourseUnit,
    Enrollment,
    EnrollmentSurvey,
    EnrollmentSurveyQuestion,
    Milestone,
    MilestoneProgress,
)
from kinesinlms.custom_app.models import CustomApp
from kinesinlms.custom_app.serializers import CustomAppSerializer
from kinesinlms.institutions.models import Institution
from kinesinlms.learning_library.constants import BlockStatus, BlockType
from kinesinlms.learning_library.models import LearningObjective, UnitBlock
from kinesinlms.learning_library.serializers import UnitBlockSerializer
from kinesinlms.sits.models import SimpleInteractiveToolTemplate
from kinesinlms.sits.serializers import SimpleInteractiveToolTemplateSerializer
from kinesinlms.speakers.models import Speaker
from kinesinlms.survey.models import Survey
from kinesinlms.survey.serializers import SurveySerializer
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


class MilestoneProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilestoneProgress
        fields = ("student", "count", "achieved", "achieved_date", "item_slugs")


class MilestoneWithProgressesSerializer(serializers.ModelSerializer):
    progresses = MilestoneProgressSerializer(many=True, read_only=True)
    milestone_id = serializers.ReadOnlyField(source="id")
    course_token = serializers.ReadOnlyField(source="course.token")

    class Meta:
        model = Milestone
        fields = (
            "milestone_id",
            "course_token",
            "slug",
            "name",
            "description",
            "type",
            "count_requirement",
            "required_to_pass",
            "progresses",
        )


class MilestoneSerializer(serializers.ModelSerializer):
    # TODO: Why was I exporing this? Shouldn't have. Commenting out.
    # milestone_id = serializers.ReadOnlyField(source="id")

    course_token = serializers.ReadOnlyField(source="course.token")

    class Meta:
        model = Milestone
        fields = (
            "course_token",
            "slug",
            "name",
            "description",
            "count_graded_only",
            "type",
            "count_requirement",
            "required_to_pass",
        )


class SimpleCourseUnitSerializer(serializers.ModelSerializer):
    """
    This serializer is used to represent a CourseUnit within
    the course navigation. So it doesn't represent the whole
    Unit, just to represent it within the navigation.
    """

    class Meta:
        model = CourseUnit
        fields = ("id", "slug", "type")


class CourseUnitSerializer(serializers.ModelSerializer):
    """
    Serializes and deserializes the CourseUnit model instance,
    and its child Blocks and related model instances
    (e.g. Assessment instances).

    Only CourseNodes of type 'UNIT' should have its 'unit'
    property set to a UnitBlock instance.
    """

    class Meta:
        model = CourseUnit
        fields = (
            "type",
            "uuid",
            "slug",
            "display_name",
            "short_description",
            "course_only",
            "enable_template_tags",
            "html_content",
            # "html_content_type",
            "json_content",
            "status",
            "unit_blocks",
            "copy_type",
        )

    # DMcQ:
    # I can't use required in this area because we have potentially
    # two types of Unit's during import (new and shallow copy)
    # so all validation really has to happen in validate() after looking
    # for copy_type.

    copy_type = serializers.CharField(required=False, write_only=True)

    uuid = serializers.UUIDField(required=False, allow_null=True)

    type = serializers.CharField(
        required=False,
        default=CourseUnitType.STANDARD.name,
        allow_null=False,
        allow_blank=False,
    )

    slug = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    display_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    short_description = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    html_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    json_content = serializers.JSONField(required=False, allow_null=True)

    status = serializers.CharField(
        required=False,
        default=BlockStatus.PUBLISHED.name,
        allow_null=False,
        allow_blank=False,
    )

    unit_blocks = UnitBlockSerializer(allow_null=True, required=False, many=True)

    def validate(self, data):
        # We required different fields depending on whether an incoming CourseUnit
        # is a shallow copy or a full CourseUnit described in JSON.
        # Therefore, the field definitions in this class have required=False,
        # but we may decide they're required here....
        copy_type = data.get("copy_type", None)
        if copy_type:
            if not data.get("uuid", None) and not data.get("slug", None):
                raise ValidationError("You must provide 'uuid' or 'slug' if 'copy_type' is set.")
        else:
            for field in ["slug", "type"]:
                if not data.get(field, None):
                    raise ValidationError(f"The '{field}' field is required.")

        # If course unit slug isn't unique, we'll append a suffix to make unique
        slug = data.get("slug", None)
        if CourseUnit.objects.filter(slug=slug).exists():
            suffix = uuid.uuid4().hex.lower()[0:6]
            data["slug"] = f"{slug}-{suffix}"

        data = super().validate(data)
        return data

    def create(self, validated_data):
        """
        When creating a CourseUnit, pop off the child unit_blocks, create the CourseUnit,
        then create and add each child UnitBlock. Link to an existing Block or create from scratch.

        Note that we may be doing a shallow copy from an existing CourseUnit and linking
        to existing blocks rather than creating an entirely new CourseUnit and related Blocks.

        Args:
            validated_data:

        Returns:
            Instance of created object
        """

        course_import_config: CourseMetaConfig = self.context.get("course_import_config", CourseMetaConfig())

        course = self.context["course"]

        # Pop the raw data so that we can send it through child serializers
        unit_blocks_raw_data = self.initial_data.pop("unit_blocks", None)
        # Pop the validated_data so that it doesn't trip up *this* serializer
        validated_data.pop("unit_blocks", None)

        copy_type = validated_data.get("copy_type", None)
        validated_uuid = validated_data.get("uuid", None)

        # Check uuid and copy type
        if copy_type == ImportCopyType.SHALLOW.name and validated_uuid is None:
            raise ValidationError(f"Cannot have copy_type SHALLOW if uuid is not set : {validated_data}")

        # Do copy or create new...
        if copy_type == ImportCopyType.SHALLOW.name:
            try:
                course_unit = self._copy_existing_course_unit(
                    course_unit_uuid=validated_uuid,
                    validated_data=validated_data,
                    course=course,
                    course_import_config=course_import_config,
                )
            except Exception:
                error_msg = f"Could not do a shallow copy of course unit from uuid {validated_uuid}."
                logger.exception(error_msg)
                raise Exception(error_msg)
        else:
            try:
                course_unit = self._create_new_course_unit(
                    validated_data=validated_data,
                    unit_blocks_raw_data=unit_blocks_raw_data,
                    course_import_config=course_import_config,
                )
            except Exception as e:
                logger.exception(f"Could not create new course unit from {validated_data} : {e}")
                error_msg = f"Could not create new course unit from {validated_data}."
                logger.exception(error_msg)
                raise Exception(error_msg)

        return course_unit

    # noinspection PyUnreachableCode
    def _copy_existing_course_unit(
        self,
        course_unit_uuid,  # noqa: F841
        validated_data,  # noqa: F841
        course: Course,  # noqa: F841
        course_import_config: CourseMetaConfig,  # noqa: F841
    ) -> Optional[CourseUnit]:
        """
        Make a sort-of shallow copy of an existing CourseUnit. We don't want to
        copy the Block instances, just link to them in the same way as the existing
        CourseUnit. So I can't say 'shallow' because we need to create new instances
        in the UnitBlock join table to link to existing Blocks. So that's why I'm fudging
        with the 'sort-of' disclaimer.

        Args:
            course_unit_uuid:
            validated_data:
            course:
            course_import_config:

        Returns:
            An instance of CourseUnit
        """

        # TEMP: Not ready for this
        raise NotImplementedError("Cannot do shallow copies yet...")
        return None

        """
        copy_fields = [
            'slug',
            'type',
            'display_name',
            'short_description',
            'course_only',
            'status',
            'html_content',
            'json_content',
        ]

        # First we'll try looking up course_unit by uuid.
        # If we can't find that, use slug but only if there are no other matches.
        if course_unit_uuid:
            try:
                existing_course_unit = CourseUnit.objects.get(uuid=course_unit_uuid)
            except CourseUnit.DoesNotExist:
                raise ValidationError(f"No CourseUnit exists with uuid {course_unit_uuid}")
        else:
            slug = validated_data.get('slug', None)
            if slug:
                course_units_with_same_slug = CourseUnit.objects.filter(slug=slug).count()
                if course_units_with_same_slug > 1:
                    raise ValidationError(f"More than one CourseUnit with slug {slug}. Use 'uuid' for exact match.")
                if course_units_with_same_slug < 1:
                    raise ValidationError(f"No uuid provided and no CourseUnit in course {course} with slug {slug}")
                existing_course_unit = CourseUnit.objects.get(slug=slug)
            else:
                raise ValidationError("Must provide 'uuid' or 'slug' for CourseUnit to copy")

        new_course_unit = CourseUnit(course=course)
        for field_name in copy_fields:
            # take incoming data first, otherwise copy
            # data from existing CourseUnit
            new_value = validated_data.get(field_name, None)
            if not new_value:
                new_value = getattr(existing_course_unit, field_name)
            setattr(new_course_unit, field_name, new_value)

        new_course_unit.save()
        unit_blocks = existing_course_unit.unit_blocks.all()
        for unit_block in unit_blocks.order_by('block_order'):
            # Cheap way to clone row in UnitBlocks is to just
            # load existing row, remove ID, set course_unit to the
            # new one we've created and then save.
            #
            # However, for assessments we use the UnitBlock to save a
            # helpful question number slug, like Q2. So if the importer
            # indicates that they want these slugs generated, we have to
            # count each assessment (since some might be new and some might be cloned)
            # and then write the slug dynamically.
            unit_block.id = None
            unit_block.course_unit_id = new_course_unit.id
            if unit_block.block.type == BlockType.ASSESSMENT.name and \
                    course_import_config.add_assessment_unit_block_slugs:
                unit_block.label = f"Q{course_import_config.assessment_index}"
                unit_block.slug = f"{course.token}_{unit_block.label}"
                course_import_config.assessment_index += 1
            else:
                unit_block.slug = None
            unit_block.save()

        return new_course_unit
        """

    def _create_new_course_unit(
        self,
        validated_data,
        unit_blocks_raw_data,
        course_import_config: CourseMetaConfig,
    ) -> CourseUnit:
        """
        Make a new CourseUnit and a UnitBlock for each block defined.
        Let the UnitBlock serializer handle creating a new Block or linking to an existing Block.

        Args:
            validated_data:
            unit_blocks_raw_data:
            course_import_config:

        Returns:
            Created CourseUnit instance

        """

        course_unit = CourseUnit.objects.create(**validated_data)
        if unit_blocks_raw_data:
            for unit_block_raw_data in unit_blocks_raw_data:
                try:
                    unit_block_serializer = UnitBlockSerializer(
                        data=unit_block_raw_data,
                        context={
                            "course_import_config": course_import_config,
                            "request": self.context.get("request", None),
                        },
                    )
                    unit_block_serializer.is_valid(raise_exception=True)
                except Exception as e:
                    logger.exception(f"Could not deserializer unit_block: {unit_block_raw_data}")
                    raise e
                unit_block: UnitBlock = unit_block_serializer.save(course_unit=course_unit)
                logger.info(f"Created unit_block: {unit_block.id}")

        return course_unit


class CourseNodeSimpleSerializer(serializers.ModelSerializer):
    """
    A *simple* CourseNode serializer is for use in things like
    navigation where we don't need to serializer any
    actual units attached to unit nodes.

    We also include specialized fields like 'content_tooltip'
    which are used by UI widgets like QuickNav.
    """

    unit = SimpleCourseUnitSerializer(many=False)
    copy_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    release_datetime = serializers.SerializerMethodField()
    release_datetime_utc = serializers.DateTimeField(source="release_datetime")

    children = serializers.SerializerMethodField(read_only=True, method_name="get_children_nodes")

    def get_release_datetime(self, obj: CourseNode):
        if obj.release_datetime:
            pst_tz = pytz.timezone("US/Pacific")
            release_datetime_pst = timezone.localtime(obj.release_datetime, pst_tz)
            return release_datetime_pst.strftime("%b %d, %Y %I:%M PST")
        return ""

    class Meta:
        model = CourseNode
        fields = (
            "id",
            "copy_type",
            "slug",
            "type",
            "purpose",
            "display_name",
            "node_url",
            "unit",
            "release_datetime",
            "release_datetime_utc",
            "content_token",
            "content_tooltip",
            "is_released",
            "link_enabled",
            "content_index",
            "display_sequence",
            "children",
        )
        read_only_fields = fields

    def get_children_nodes(self, obj):
        """self referral field"""
        serializer = CourseNodeSimpleSerializer(instance=obj.children.all().order_by("display_sequence"), many=True)
        return serializer.data


class CourseNodeSerializer(serializers.ModelSerializer):
    """
    A *full* serializer for CourseNodes, meaning it includes
    the 'course_unit' property which points to a CourseUnit model,
    which has its own complete subtree of Block content.

    During export this serializer should be able to export the
    CourseUnit property completely, all the way down to e.g. Assessment
    attached to a SubBlock.

    During import this serializer should be able to create (or link, in the
    case of Blocks with UUIDs) all necessary CourseUnit and Block model
    instances from an exported CourseNode tree.
    """

    unit = CourseUnitSerializer(required=False, allow_null=True)
    node_url = serializers.CharField(read_only=True)

    # We expect each node to have this value defined, as it is vital to order.
    display_sequence = serializers.IntegerField(
        required=True,
        allow_null=False,
    )

    class Meta:
        model = CourseNode
        fields = (
            "slug",
            "display_name",
            "type",
            "purpose",
            "node_url",
            "release_datetime",
            "content_index",
            "display_sequence",
            "unit",
            "children",
        )

    def get_fields(self):
        # DMcQ: I think this approach is needed to do recursive DRF deserialization?
        # DMcQ: (Why can't I just put CourseNodeSerializer above as a property with the others?)
        fields = super().get_fields()
        fields["children"] = CourseNodeSerializer(many=True, read_only=True)
        return fields


class CourseMetaSerializer(serializers.ModelSerializer):
    """
    A 'simple' serializer for things like analytics.
    """

    class Meta:
        model = Course
        fields = (
            "id",
            "slug",
            "run",
            "token",
            "num_enrolled",
            "display_name",
            "short_name",
            "start_date",
            "end_date",
            "advertised_start_date",
            "enrollment_start_date",
            "enrollment_end_date",
            "self_paced",
            "days_early_for_beta",
            "enable_certificates",
            # 'start_sequence_at'
        )


class LearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = ("slug", "description")

    def create(self, validated_data) -> LearningObjective:
        slug = validated_data["slug"]
        try:
            lo = LearningObjective.objects.get(slug=slug)
        except LearningObjective.DoesNotExist:
            lo = LearningObjective.objects.create(**validated_data)
        return lo


class LearningObjectiveSerializerField(serializers.Field):
    def to_representation(self, value) -> List[LearningObjective]:
        los = LearningObjectiveSerializer(instance=value, many=True).data
        return los

    def to_internal_value(self, data) -> List[dict]:
        """
        Read in a list of learning objectvies json objects.
        Create any LOs that don't exist in the DB.

        Args:
            A json list of objects defining LOs that either
            already exist in the DB or need to be created.

        Returns:
            A list of created or linked LearningObjective model instances.
        """
        logger.info(f"data: {data}")
        if not data:
            return []
        los = []
        if not isinstance(data, list):
            raise ValidationError("learning_objectives field must be a list")
        for item in data:
            slug = item["slug"]
            try:
                lo = LearningObjective.objects.get(slug=slug)
            except LearningObjective.DoesNotExist:
                try:
                    serializer = LearningObjectiveSerializer(data=item)
                    serializer.is_valid(raise_exception=True)
                    lo = serializer.save()
                except Exception as e:
                    logger.exception("Could not deserializer LO")
                    raise e
            los.append(lo)
        return los


class EnrollmentSurveyQuestionSerializer(serializers.ModelSerializer):
    """
    ModelSerializer for EnrollmentSurveyQuestions
    """

    class Meta:
        model = EnrollmentSurveyQuestion
        fields = ("question_type", "question", "definition", "display_order")


class CourseResourceSerializer(serializers.ModelSerializer):
    """
    ModelSerializer for CourseResources
    """

    uuid = serializers.UUIDField()

    class Meta:
        model = CourseResource
        fields = ("uuid", "name", "description")


class EnrollmentSurveySerializer(serializers.ModelSerializer):
    """
    ModelSerializer for EnrollmentSurveys (usually attached to a course
    as part of an import definition).
    """

    questions = EnrollmentSurveyQuestionSerializer(many=True, required=True)

    class Meta:
        model = EnrollmentSurvey
        fields = ["questions"]


class CohortSerializer(serializers.ModelSerializer):
    """
    Handles serializing/deserializing cohorts related to a course.
    """

    class Meta:
        model = Cohort
        fields = ("institution",)


class CourseSerializer(TaggitSerializer, serializers.ModelSerializer):
    """
    A *full* serializer for Courses, with serializers for all related child elements.
    This serializer is for things like import and export.
    """

    token = serializers.CharField(read_only=True)
    catalog_description = CourseCatalogDescriptionSerializer(
        many=False,
        required=True,
    )
    surveys = SurveySerializer(many=True, required=False)

    # TODO: Use CourseNodeSerializer as part of import process
    # TODO: For now, course_root_node is read_only. Input deserialization happens
    # TODO: in custom methods in composer/views.py
    course_root_node = CourseNodeSerializer(read_only=True)

    custom_apps = CustomAppSerializer(many=True, required=False)

    milestones = MilestoneSerializer(many=True, required=False)

    badge_classes = BadgeClassSerializer(many=True, required=False)

    speakers = SlugRelatedField(slug_field="slug", many=True, allow_null=True, queryset=Speaker.objects.all())

    learning_objectives = LearningObjectiveSerializerField(required=False, default=[])

    simple_interactive_tool_templates = SimpleInteractiveToolTemplateSerializer(
        many=True,
        allow_null=True,
        required=False,
    )

    certificate_template = CertificateTemplateSerializer(
        many=False,
        allow_null=True,
        required=False,
    )

    enrollment_survey = EnrollmentSurveySerializer(
        many=False,
        allow_null=True,
        required=False,
    )

    course_resources = CourseResourceSerializer(
        many=True,
        required=False,
    )

    cohorts = CohortSerializer(
        read_only=True,
        many=True,
    )

    # Shortcut write-only field that allows you to provide
    # slugs of existing institutions and cohorts will be created for each.
    cohort_institutions = serializers.ListField(
        write_only=True,
        required=False,
        child=serializers.CharField(),
    )

    course_home_content = SanitizedHTMLField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    tags = TagListSerializerField(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Course
        fields = (
            "slug",
            "run",
            "display_name",
            "short_name",
            "start_date",
            "end_date",
            "tags",
            "advertised_start_date",
            "enrollment_start_date",
            "enrollment_end_date",
            "admin_only_enrollment",
            "self_paced",
            "enable_course_outline",
            "days_early_for_beta",
            "enable_certificates",
            "token",
            "custom_apps",
            "catalog_description",
            "course_root_node",
            "enable_badges",
            "milestones",
            "course_resources",
            "speakers",
            "surveys",
            "badge_classes",
            "learning_objectives",
            "cohorts",
            "cohort_institutions",
            "simple_interactive_tool_templates",
            "certificate_template",
            "enable_enrollment_survey",
            "enrollment_survey",
            "course_home_content",
        )

    def to_representation(self, instance):
        """
        This is kind of kludgy, but simplest way I can figure out to remove
        redundant definitions of blocks, which happens when we e.g. have a course
        with an assessment shown twice.

        NOTE: We don't need to do this for read-only blocks as that is handled in the UnitBlock Serializer.
        """
        course_dict = super(CourseSerializer, self).to_representation(instance)

        block_uuids = []
        for module_dict in course_dict["course_root_node"]["children"]:
            sections_dict = module_dict["children"]
            for section_dict in sections_dict:
                units_dict = section_dict["children"]
                for unit_dict in units_dict:
                    unit_blocks_dict = unit_dict["unit"]["unit_blocks"]
                    for unit_block_dict in unit_blocks_dict:
                        try:
                            block = unit_block_dict["block"]
                        except KeyError as ke:
                            logger.error("Can't find 'block' key in unit_block")
                            raise ke
                        block_uuid = block["uuid"]
                        read_only = unit_block_dict["read_only"]
                        if block_uuid in block_uuids and not read_only:
                            # Not first instance of block.
                            # So update this Block json to just include uuid as that's all that
                            # will be needed to link to existing block during import.
                            # ( If the block was read_only it's already been slimmed )

                            slim_block = OrderedDict()
                            slim_block["uuid"] = block_uuid
                            # Include 'type' just for reference for someone reading raw json
                            try:
                                slim_block["type"] = block["type"]
                            except Exception:
                                logger.exception("why?")
                            # Replace full dictionary with slim version
                            unit_block_dict["block"] = slim_block
                        else:
                            block_uuids.append(block_uuid)

        return course_dict

    def create(self, validated_data):
        # Remove nested relationships from incoming data.
        # Otherwise, DRF complains with "The `.create()` method does not support
        # writable nested fields by default."

        logger.debug("Course serializer creating Course model and related:")

        # Handle Course Catalog Description
        course_description_data = validated_data.pop("catalog_description")
        cat_description = CourseCatalogDescription.objects.create(**course_description_data)

        # We've already handled learning_objectives in the serializer field, so pop off here
        validated_data.pop("learning_objectives", None)

        # Don't create root CourseNode...that happens in a separate part
        # of the course import process
        validated_data.pop("course_root_node", None)

        # Pop off the following and don't create until we create course itself...
        try:
            enrollment_survey_validated_data: Dict = validated_data.pop("enrollment_survey")
        except KeyError:
            enrollment_survey_validated_data: Dict = {}

        try:
            custom_apps_validated_data = validated_data.pop("custom_apps")
        except KeyError:
            custom_apps_validated_data = []

        try:
            speakers_validated_data = validated_data.pop("speakers")
        except KeyError:
            speakers_validated_data = []

        try:
            sit_templates_validated_data = validated_data.pop("simple_interactive_tool_templates")
        except KeyError:
            sit_templates_validated_data = []

        try:
            milestones_validated_data = validated_data.pop("milestones")
        except KeyError:
            milestones_validated_data = []

        try:
            surveys_validated_data = validated_data.pop("surveys")
        except KeyError:
            surveys_validated_data = []

        try:
            badge_classes = validated_data.pop("badge_classes")
        except KeyError:
            badge_classes = []

        try:
            course_resources = validated_data.pop("course_resources")
        except KeyError:
            course_resources = []

        try:
            certificate_template_data = validated_data.pop("certificate_template")
        except KeyError:
            certificate_template_data = None

        try:
            cohort_institutions_validated_data = validated_data.pop("cohort_institutions")
        except KeyError:
            cohort_institutions_validated_data = None

        course = CourseFactory.create(
            **validated_data,
            catalog_description=cat_description,
            create_course_root_node=False,
        )
        logger.info(f" - created course  : {course}")

        # Create and/or link related instances
        # ......................................

        # ...create-and-link custom apps
        for custom_app_validated_data in custom_apps_validated_data:
            custom_app = CustomApp.objects.create(**custom_app_validated_data, course=course)
            logger.info(f" - created custom app : {custom_app}")

        # ...create SIT templates apps ... they'll be linked by SITs in units if they appear
        for sit_template_validated_data in sit_templates_validated_data:
            if isinstance(sit_template_validated_data, SimpleInteractiveToolTemplate):
                # SIT Template already exists. No need to create it here. Any blocks
                # that refer to it via slug will be linked later on in the Block serializer.
                logger.warning(f"Skipping SIT template slug {sit_template_validated_data.slug} ... it already exists.")
            else:
                # SIT Template does not exist. So we have to create it here so that it's available later
                # for any Blocks that link to it.
                sit_template = SimpleInteractiveToolTemplate.objects.create(**sit_template_validated_data)
                logger.info(f" - created SIT template : {sit_template}")

        # ...then link speakers (they should already exist)
        for speaker_validated_data in speakers_validated_data:
            try:
                course.speakers.add(speaker_validated_data)
                logger.info(f" - linked speaker {speaker_validated_data}")
            except Exception:
                logger.exception(f"Could not link speaker {speaker_validated_data} to course {course}")

        # ...then create milestones
        for milestone_validated_data in milestones_validated_data:
            milestone = Milestone.objects.create(**milestone_validated_data, course=course)
            logger.info(f" - created milestone {milestone}")

        # ...then create and link surveys
        for survey_validated_data in surveys_validated_data:
            survey = Survey.objects.create(**survey_validated_data, course=course)
            logger.info(f" - created survey {survey}")

        # ...thn create or link course resources
        # We don't load the actual file in at this point. We'll let our archive importer
        # do that once the entire course.json has been deserialized.
        for course_resource_validated_data in course_resources:
            course_resource_uuid = course_resource_validated_data.get("uuid", None)
            if not course_resource_uuid:
                raise Exception(f"CourseResource object is missing uuid: {course_resource_validated_data}")
            course_resource, created = CourseResource.objects.get_or_create(course=course, uuid=course_resource_uuid)
            course_resource.name = course_resource_validated_data.get("name", None)
            course_resource.description = course_resource_validated_data.get("description", None)
            course_resource.save()

        # ...then link or create-and-link badge classes
        for badge_class_validated_data in badge_classes:
            # DRF will have changed the slug string to a BadgeClass instance
            slug = badge_class_validated_data.get("slug", None)
            if not slug:
                raise Exception(f"BadgeClass object is missing slug: {badge_class_validated_data}")
            try:
                badge_class = BadgeClass.objects.get(slug=slug)
                logger.info(f"Linked course to existing badge class :{badge_class}")
            except BadgeClass.DoesNotExist:
                badge_class = BadgeClass.objects.create(**badge_class_validated_data)
                logger.info(f"Created new badge class :{badge_class}")
            course.badge_classes.add(badge_class)

        # ...then cohorts

        # NOTE: Don't forget that at this point a CohortForumGroup hasn't
        # been created, so any Cohort instance created for this course won't be
        # able to set the cohort's cohort_forum_group property.
        # We'll have to add a CohortForumGroup to each at a later step.
        # (If this serializer was invoked through course_create_from_json(), that
        # method will handle this Discourse setup in a later step.)
        if cohort_institutions_validated_data:
            for cohort_institution_slug in cohort_institutions_validated_data:
                try:
                    institution = Institution.objects.get(slug=cohort_institution_slug)
                    cohort, created = Cohort.objects.get_or_create(
                        course=course,
                        institution=institution,
                        type=CohortType.CUSTOM.name,
                        slug=f"cohort-{course.slug}-{cohort_institution_slug}",
                        # We don't know cohort_forum_group yet so can't set it
                        # cohort_forum_group=""
                    )
                    cohort.name = f"Cohort for {institution.name}"
                    cohort.save()
                except Institution.DoesNotExist:
                    logger.error(f"Could not create cohort for institution slug: {cohort_institution_slug}")
                except Exception as e:
                    logger.error(f"Could not create cohort for institution slug: {cohort_institution_slug} : {e}")

        # Handle enrollment survey if defined...
        if enrollment_survey_validated_data:
            enrollment_survey = EnrollmentSurvey.objects.create(course=course)
            questions_validated_data = enrollment_survey_validated_data.pop("questions")
            for question_validated_data in questions_validated_data:
                question = EnrollmentSurveyQuestion.objects.create(**question_validated_data)
                enrollment_survey.questions.add(question)
            logger.info(f"Created enrollment survey: {enrollment_survey}")

        # Handle custom certificate data if defined...
        if certificate_template_data:
            template_name = certificate_template_data.get("custom_template_name", None)
            certificate_template, created = CertificateTemplateFactory.get_or_create_certificate_template(course=course)
            certificate_template.custom_template_name = template_name
            certificate_template.save()
            logger.info(f"Created certificate template: {certificate_template}")

            signatories = []
            for signatory_data in certificate_template_data["signatories"]:
                slug = signatory_data.get("slug", None)
                if slug:
                    try:
                        s = Signatory.objects.get(slug=slug)
                    except Signatory.DoesNotExist:
                        raise Exception(
                            f"Signatory with slug {slug} does not exist. "
                            f"Create a certificate signatory with this slug before importing this course."
                        )
                else:
                    signatory_serializer = SignatorySerializer(**signatory_data)
                    signatory_serializer.is_valid(raise_exception=True)
                    s = signatory_serializer.save()
                signatories.append(s)
            if signatories:
                for signatory in signatories:
                    certificate_template.signatories.add(signatory)
                certificate_template.save()

        return course


class BookmarkSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Bookmark
        fields = ("student", "course", "unit_node", "id")

    def validate(self, data):
        student = self.context["request"].user
        course = data.get("course", None)
        if not student:
            raise ValidationError("Student must be defined")
        if not course:
            raise ValidationError("Course must be defined")
        try:
            Enrollment.objects.get(course=course, student=student, active=True)
        except Enrollment.DoesNotExist:
            raise ValidationError(f"User {student.username} is not actively enrolled in this course.")
        bookmark_count = Bookmark.objects.filter(student=student, course=course).count()
        if bookmark_count > 200:
            raise ValidationError("You can only have 200 or fewer bookmarks per course.")

        return data

    def create(self, validated_data):
        """
        Override ``create`` to provide a user via request.user by default.
        This is required since the read_only ``user`` field is not included by
        default anymore since
        https://github.com/encode/django-rest-framework/pull/5886.
        We also write a tracking event for every bookmark created.
        """
        if "student" not in validated_data:
            validated_data["student"] = self.context["request"].user

        bookmark = super().create(validated_data)

        # Track this bookmark interaction...
        unit_node = bookmark.unit_node
        course_unit = unit_node.unit
        Tracker.track(
            event_type=TrackingEventType.BOOKMARK_CREATED.value,
            user=bookmark.student,
            event_data=None,
            course=bookmark.course,
            unit_node_slug=unit_node.slug,
            course_unit_id=course_unit.id,
            course_unit_slug=course_unit.slug,
            block_uuid=None,
        )

        return bookmark


class IBiologyCoursesCourseSerializer(CourseSerializer):
    """
    Handles deserializing a course exported in IBIO_COURSES_FORMAT.

    We need to update the JSON to match what our serializer expects
    """

    def to_internal_value(self, data) -> Course:
        """
        Update structure of incoming iBiology Courses course export format
        to match the structure of the JSON expected by the CourseSerializer.

        This way, we can use the base CourseSerializer to create the course.

        """

        # Take off testimonials we don't import those.
        if "testimonials" in data["catalog_description"]:
            data["catalog_description"].pop("testimonials", None)

        # Manually create speakers if they don't exist
        if "speakers" in data:
            for speaker_slug in data["speakers"]:
                speaker, created = Speaker.objects.get_or_create(slug=speaker_slug)
                if created:
                    logger.info(f"Creating missing speaker: {speaker_slug}")

        # Take syllabus url off if it exists and create Syllabus file object manually
        syllabus_url = data["catalog_description"].pop("syllabus_url", None)

        # Update the course_root_node to match the KinesinLMS format
        # so we can use the same CourseNodeSerializer to create the course.
        course_root_node = data.get("course_root_node", None)
        if course_root_node:
            self._process_node(course_root_node)

        course = super().to_internal_value(data)

        # Add in the syllabus file to the course if we created it
        if syllabus_url:
            self._load_syllabus_from_url(
                catalog_description=course.catalog_description,
                syllabus_url=syllabus_url,
            )

        return course

    def _process_node(self, node: Dict):
        """
        Recursive function to process nodes in the course nav tree.
        """
        if "children" in node:
            for child in node["children"]:
                self._process_node(child)
        if "unit" in node:
            # This is a unit node, so make any required changes to
            # the "unit" dictionary, which represents a CourseUnit.
            unit = node["unit"]
            unit_blocks = unit.get("unit_blocks", None)
            for key, block in unit_blocks.items():
                self._process_block(block)

    def _process_block(self, block: Dict):
        """
        Process a block in the course nav tree.
        """
        block_type = block.get("type")
        if block_type == "DISCOURSE_TOPIC":
            block["type"] = BlockType.FORUM_TOPIC.name

        html_content = block.get("html_content")
        if html_content is not None:
            block["html_content"] = self._update_template_keywords(html_content)

    def _update_template_keywords(self, html_content: str) -> str:
        """
        Transform any SCL-style template keywords to
        Kinesin-style template tags.
        """
        if not html_content:
            return html_content

        replacements = {
            # Simple keywords
            r"\[\[\s*ANON_USER_ID\s*\]\]": "{% anon_user_id %}",
            r"\[\[\s*USERNAME\s*\]\]": "{% username %}",
            # Replace LINK keywords with appropriate template tag.
            r"##MODULE_LINK\[\s*(\d+)\s*\]##": "{{% module_link {} %}}",
            r"##SECTION_LINK\[\s*(\d+)\s*,\s*(\d+)\s*\]##": "{{% section_link {} {} %}}",
            r"##UNIT_LINK\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]##": "{{% unit_link {} {} {} %}}",
            # Other keywords...
            # Transform UNIT_SLUG_LINK
            r"##UNIT_SLUG_LINK\[\s*([A-Za-z\d\-\_]+)\s*\]##": "{{% unit_slug_link {} %}}",
        }

        for pattern, replacement in replacements.items():
            html_content = re.sub(pattern, lambda match: replacement.format(*match.groups()), html_content)

        return html_content

    def _load_syllabus_from_url(
        self,
        catalog_description: CourseCatalogDescription,
        syllabus_url: str,
    ):
        """
        In the older iBiology Courses format, the syllabus was stored as a URL.
        In KinLMS, we store the syllabus as a file object.

        So create that file object with the incoming URL and then attach it to the course
        description.

        Args:
            catalog_description (CourseCatalogDescription): _description_
            syllabus_url (str): _description_
        """
        response = requests.get(syllabus_url, allow_redirects=True)
        if response.status_code == 200:
            # Get filename from URL or use default
            filename = syllabus_url.split("/")[-1]
            if not filename:
                filename = "syllabus.pdf"

            # Create file object and save
            lf = NamedTemporaryFile()
            lf.write(response.content)
            lf.flush()

            catalog_description.syllabus.save(
                filename,
                File(open(lf.name, "rb")),
                save=True,
            )
            logger.info(f" - downloaded and saved syllabus from URL: {syllabus_url}")
        else:
            logger.error(f"Could not download syllabus from URL: {syllabus_url}")
