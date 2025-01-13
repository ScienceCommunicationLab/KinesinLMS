import logging
import uuid
from collections import OrderedDict

from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from taggit.serializers import TaggitSerializer

from kinesinlms.assessments.models import Assessment
from kinesinlms.assessments.serializers import AssessmentAllDataSerializer
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import (
    Block,
    BlockResource,
    LearningObjective,
    Resource,
    UnitBlock,
)
from kinesinlms.sits.models import SimpleInteractiveTool
from kinesinlms.sits.serializers import SimpleInteractiveToolImportSerializer
from kinesinlms.speakers.models import Speaker
from kinesinlms.survey.models import Survey, SurveyBlock

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Serializers for Learning Library
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# This is very much in flux as I try to figure out how to expose models
# to client for "Learning Library" feature


class PublicResourceSerializer(TaggitSerializer, serializers.ModelSerializer):
    pass
    # tags = TagListSerializerField()
    # class Meta:
    #    model = PublicResource
    #    fields = ('type',
    #             'display_name',
    #             'tags',
    #             'html_content',
    #             'json_content')


class ResourceSerializer(serializers.ModelSerializer):
    def validate_uuid(self, uuid_value):
        """
        We want to validate that the uuid is a valid uuid, but not that it's unique.
        (It's ok if it already exists in DB.)
        So we set validators to empty list in the field definition, meanwhile we
        define any checks in this function.
        """
        try:
            uuid.UUID(uuid_value)
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format.")

        return uuid_value

    def validate_slug(self, slug_value):
        """
        If a Resource with this slug already exists in DB, we'll append a uuid to it.
        """
        if Resource.objects.filter(slug=slug_value).exists():
            slug_value = f"{slug_value}_{uuid.uuid1()}"
        return slug_value

    uuid = serializers.CharField(required=True, allow_null=False, allow_blank=False, validators=[])

    class Meta:
        model = Resource
        fields = (
            "type",
            "slug",
            "uuid",
            "file_name",
        )


class SurveyBlockSerializer(serializers.ModelSerializer):
    survey = serializers.SlugRelatedField(
        queryset=Survey.objects.all(),
        slug_field="slug",
        required=True,
        allow_null=False,
    )

    class Meta:
        model = SurveyBlock
        fields = ("survey",)


class BlockSerializer(serializers.ModelSerializer):
    # Block to Assessment is one-to-one
    # Note that type is not required...when we want to use the same
    # Block as defined earlier in a course import, we use the slug
    # without the type.

    type = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    slug = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    uuid = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    enable_template_tags = serializers.BooleanField(required=False, default=True)

    display_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    short_description = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    html_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    json_content = serializers.JSONField(required=False, allow_null=True)

    simple_interactive_tool = SimpleInteractiveToolImportSerializer(required=False, allow_null=True)

    assessment = AssessmentAllDataSerializer(required=False, allow_null=True)

    speakers = serializers.SlugRelatedField(
        queryset=Speaker.objects.all(),
        many=True,
        slug_field="slug",
        required=False,
        allow_null=True,
    )

    learning_objectives = serializers.SlugRelatedField(
        queryset=LearningObjective.objects.all(),
        many=True,
        slug_field="slug",
        required=False,
        allow_null=True,
    )

    resources = ResourceSerializer(
        many=True,
        required=False,
        allow_null=True,
    )

    survey_block = SurveyBlockSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Block
        fields = (
            "type",
            "slug",
            # 'tags',
            "uuid",
            "display_name",
            "short_description",
            "course_only",
            "enable_template_tags",
            "html_content",
            "survey_block",
            # "html_content_type",
            "json_content",
            "assessment",
            "simple_interactive_tool",
            "speakers",
            "learning_objectives",
            "resources",
        )

    def validate(self, data):
        """
        Object-level validation for block.
        """

        data = super().validate(data)

        block_type = data.get("type", None)
        # Validations specific to FORUM_TOPIC blocks
        if block_type == BlockType.FORUM_TOPIC.name:
            if not data["slug"]:
                raise serializers.ValidationError("FORUM_TOPIC blocks must have a slug")
            if not data["display_name"]:
                logger.warning(f"FORUM_TOPIC block does not have display name: {data}")
                # raise serializers.ValidationError("FORUM_TOPIC blocks must have a display_name")

        speakers = data.get("speakers", None)
        if speakers and len(speakers) > 0 and block_type != BlockType.VIDEO.name:
            raise serializers.ValidationError("Cannot attach speakers to a non-VIDEO block.")

        return data

    def create(self, validated_data):
        """
        Create any related models first, then create and save the block.
        """

        validated_assessment_data = validated_data.pop("assessment", None)

        validated_survey_block_data = validated_data.pop("survey_block", None)

        validated_sit_data = validated_data.pop("simple_interactive_tool", None)

        block_type = validated_data.get("type", None)
        if not block_type:
            raise Exception("The 'type' property must be set when creating new blocks")

        if block_type == BlockType.ASSESSMENT.name and validated_assessment_data is None:
            ValidationError(f"Blocks of type {block_type} must define an Assessment.")

        speakers = validated_data.pop("speakers", None)

        resources_data = validated_data.pop("resources", None)

        block = Block.objects.create(**validated_data)

        if speakers:
            if block.type == BlockType.VIDEO.name:
                for speaker in speakers:
                    block.speakers.add(speaker)
                    block.save()
            else:
                logger.warning(
                    f"IGNORING speakers. Block {block} has speakers defined, but speakers "
                    f"are only valid for {BlockType.VIDEO.name}-type blocks."
                )

        if validated_assessment_data:
            assessment = Assessment.objects.create(**validated_assessment_data, block=block)
            logger.info(f"Created assessment {assessment} for block {block}")

        if validated_survey_block_data:
            try:
                survey = Survey.objects.get(slug=validated_survey_block_data["survey"].slug)
                survey_block = SurveyBlock.objects.create(block=block, survey=survey)
                logger.info(f"Created survey_block {survey_block} for block {block}")
            except Survey.DoesNotExist:
                logger.error(f"Survey with slug {validated_survey_block_data['survey']} does not exist.")
                raise

        if validated_sit_data:
            sit = SimpleInteractiveTool.objects.create(**validated_sit_data, block=block)
            logger.info(f"Created SIT {sit} for block {block}")

        if resources_data:
            # If this block has resources, we'll link to existing Resources if they
            # already exist, otherwise we'll create them.
            # Also, we don't load the actual file in at this point. We'll let our archive importer
            # do that once the entire course.json has been deserialized.
            for resource_data in resources_data:
                resource, resource_created = Resource.objects.get_or_create(uuid=resource_data["uuid"])
                if resource_created:
                    resource.type = resource_data["type"]
                    resource.slug = resource_data["slug"]
                    resource.save()
                else:
                    if resource.type != resource_data["type"]:
                        raise Exception(
                            f"Resource {resource} already exists but types don't match: "
                            f"Existing: {resource.type} New: {resource['type']}"
                        )

                block_resource, block_resource_created = BlockResource.objects.get_or_create(
                    block=block, resource=resource
                )

                if resource_created:
                    logger.info(
                        f"Created block_resource {block_resource} " f"and resource {resource} and for block {block}"
                    )
                else:
                    logger.info(
                        f"Created block_resource {block_resource} "
                        f"to linked to existing resource {resource} "
                        f"and block {block}"
                    )

        return block

    def get_survey(self, obj):
        """
        Get the survey ID from the related SurveyBlock if it exists.
        Returns None if no survey is associated.
        """
        try:
            survey_block = obj.survey_block
            return survey_block.survey_id if survey_block else None
        except AttributeError:
            return None


class UnitBlockSerializer(serializers.ModelSerializer):
    block = BlockSerializer(required=True, many=False, allow_null=False)

    class Meta:
        model = UnitBlock
        fields = (
            "label",
            "index_label",
            "block_order",
            "hide",
            "read_only",
            "include_in_summary",
            "block",
        )

    def create(self, validated_data):
        """
        Transform a 'unit_block' json object into UnitBlock instance.
        Create the Block if it doesn't already exist. If it exists, simply link to it.
        If creating a new Block, pop off any speakers or learning objectives
        linked to that block and either link them if they exist, or create and link them.

        """

        course_import_config = self.context.get("course_import_config", None)
        request = self.context.get("request", None)

        read_only = validated_data.get("read_only", False)

        # Pop off block json
        # Pop the raw data so that we can send it through child serializers
        block_raw_data = self.initial_data.pop("block", None)
        # Pop the validated_data so that it doesn't trip up *this* serializer
        block_validated_data = validated_data.pop("block", None)
        block_slug = block_validated_data.get("slug", None)

        # DRF will have transformed learning objective slug into LearningObjective
        # model instance via the 'slugRelatedField'. So manually pop both raw and validated
        # data here and then attach validated data the save (if present).
        # (We have to pop raw data off too so that it doesn't confuse the Block serializer.)
        block_raw_data.pop("learning_objectives", None)
        learning_objectives_validated_data = block_validated_data.pop("learning_objectives", None)

        block_uuid = block_validated_data.get("uuid", None)
        block_instance = None
        if block_uuid:
            try:
                block_instance = Block.objects.get(uuid=block_uuid)
                logger.info(f"BLOCK UUID LINK: Linking to existing block : {block_uuid}")
            except Block.DoesNotExist:
                # Block doesn't exist in library, so we'll creat it next step...
                logger.warning(
                    f"BLOCK UUID LINK: Block uuid is {block_uuid} but no existing block "
                    f"with that uuid. Therefore, creating a new block with this uuid."
                )
        elif read_only and block_slug:
            # If the UnitBlock is read_only, the course json author might want to link to another
            # Block defined in the same JSON. So look that block up by slug
            try:
                block_instance = Block.objects.get(slug=block_slug)
            except Block.DoesNotExist:
                raise Exception(f"Cannot find read_only UnitBlock by slug {block_slug}")
            except IntegrityError:
                raise Exception(
                    f"Cannot link read_only UnitBlock linked by slug: More than one block with slug {block_slug}"
                )

        if not block_instance:
            logger.info("Creating new Block ...")

            # Creating new block...
            try:
                serializer = BlockSerializer(
                    data=block_raw_data,
                    context={
                        "course_import_config": course_import_config,
                        "request": request,
                    },
                )
                serializer.is_valid()
                block_instance = serializer.save()
            except Exception as e:
                logger.error(f"Could not deserialize block error: {e} Block : {block_raw_data}")
                raise e

            # ... and linking LOs
            if learning_objectives_validated_data:
                for lo in learning_objectives_validated_data:
                    block_instance.learning_objectives.add(lo)

        # Create the UnitBlock...we'll attach the Block instance further below.
        validated_data["block"] = block_instance
        unit_block: UnitBlock = super(UnitBlockSerializer, self).create(validated_data)

        return unit_block

    def to_representation(self, instance):
        data = super(UnitBlockSerializer, self).to_representation(instance)
        if instance.read_only:
            # If this is a read-only UnitBlock, we don't want to copy in the entire
            # Block json, just the block's uuid.
            logger.debug(f"data: {data}")
            simplified_block_dict = OrderedDict()
            simplified_block_dict["uuid"] = data["block"]["uuid"]
            simplified_block_dict["type"] = data["block"]["type"]
            data["block"] = simplified_block_dict
        return data


"""
 # Earlier in V2 development I was using the Assessments slug to look up things
            # like printable review. But I should have been using a slug field
            # on UnitBlock. So when reading in early v2 exported courses copy that over.
            if block.type == BlockType.ASSESSMENT.name:
                # if user is auto-numbering assessments, we don't care about any slugs
                # defined in assessment
                if course_import_config.add_assessment_unit_block_slugs:
                    unit_block.label = f"Q{course_import_config.assessment_index}"
                    unit_block.slug = f"{course_unit.course.token}_{unit_block.label}"
                    course_import_config.assessment_index += 1
                else:

                    # User is not auto-numbering assessments, so just use default mechanism
                    # for UnitBlock slug and label creation.
                    if not block.assessment.slug:
                        block.assessment.slug = f"assessment_{uuid.uuid1()}"
                        block.assessment.save()

                    # Create a slug for the UnitBlock based on the Assessment Block's slug...
                    unit_block.slug = f"{course_unit.course.token}_{block.assessment.slug}"

                    # Create a label based on info in Assessment block...
                    if hasattr(block, 'display_name'):
                        unit_block.label = block.display_name
                    else:
                        unit_block.label = None
                        
                        """
