import logging
import sys
from typing import Dict

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from kinesinlms.course.tasks import track_milestone_progress
from kinesinlms.course.utils import user_is_enrolled
from kinesinlms.sits.constants import DEFAULT_MAX_TABLETOOL_ROWS_ALLOWED, SimpleInteractiveToolSubmissionStatus
from kinesinlms.sits.models import SimpleInteractiveToolSubmission, SimpleInteractiveTool, \
    SimpleInteractiveToolTemplate, \
    SimpleInteractiveToolType
from kinesinlms.sits.schema import DiagramToolDefinition, \
    TableToolDefinition
from kinesinlms.sits.tasks import track_simple_interactive_tool_submission

logger = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
def validate_sit_definition(tool_type: str, definition: Dict):
    # Make sure json fields are valid
    if definition:
        if tool_type == SimpleInteractiveToolType.DIAGRAM.name:
            try:
                DiagramToolDefinition.from_dict(definition)
            except Exception as e:
                raise ValidationError(f"Invalid diagram tool 'definition' JSON: {e}")
        elif tool_type == SimpleInteractiveToolType.TABLETOOL.name:
            try:
                TableToolDefinition.from_dict(definition)
            except Exception as e:
                raise ValidationError(f"Invalid table tool 'definition' JSON: {e}")
        else:
            error_msg = f"#SimpleInteractiveToolSerializer: Cannot validate definition " \
                        f"for SimpleInteractiveTool type: {tool_type} because " \
                        f"no validating dataclass is defined for this type."
            logger.error(error_msg)
            raise ValidationError(error_msg)


class SimpleInteractiveToolImportSerializer(serializers.ModelSerializer):
    """
    This serializer meant to be used during course imports.
    It's not meant for student use.
    """

    graded = serializers.BooleanField(default=False,
                                      required=False,
                                      allow_null=False)

    template = serializers.SlugRelatedField(slug_field="slug",
                                            required=False,
                                            allow_null=True,
                                            allow_empty=True,
                                            queryset=SimpleInteractiveToolTemplate.objects.all(),
                                            many=False)

    class Meta:
        model = SimpleInteractiveTool
        fields = ('slug',
                  'name',
                  'tool_type',
                  'instructions',
                  'graded',
                  'definition',
                  'template')

    def validate(self, data):
        """
        Validate incoming data for this SIT.
        Use dataclasses to validate portion of json
        that will be stored in JSON field.
        """
        data = super(SimpleInteractiveToolImportSerializer, self).validate(data)
        tool_type = data.get('tool_type')
        definition = data.get('definition', {})
        validate_sit_definition(tool_type=tool_type,
                                definition=definition)
        return data

    def create(self, validated_data):
        """
        If the uuid is provided, this SimpleInteractiveTool should already
        exist so just load it and return from library. Otherwise,
        create it.
        """
        uuid = validated_data.get("uuid", None)
        if uuid:
            raise NotImplemented("Importing by uuid is not implemented yet.")
        sit = SimpleInteractiveTool.objects.create(**validated_data)
        return sit


class SimpleInteractiveToolSerializer(serializers.ModelSerializer):
    """
    This serializer is used for admin views in the API. This API endpoint
    might be used by KinesinLMS analytics.
    The endpoint requirements might be a little different from the import
    requirements, which is why we have this serializer and
    SimpleInteractiveToolImportSerializer.

    This serializer is not meant for student use.

    """

    template = serializers.SlugRelatedField(slug_field="slug",
                                            queryset=SimpleInteractiveToolTemplate.objects.all(),
                                            many=False)

    graded = serializers.BooleanField(default=False,
                                      required=False,
                                      allow_null=False)

    definition = serializers.JSONField(allow_null=True,
                                       default={})

    class Meta:
        model = SimpleInteractiveTool

        fields = ('id',
                  'slug',
                  'block',
                  'name',
                  'tool_type',
                  'definition',
                  'graded',
                  'template',
                  'max_score')

        read_only_fields = ('max_score',)

    def validate(self, data):
        """
        Validate incoming data for this SIT.
        Use dataclasses to validate portion of json
        that will be stored in JSON field.
        """
        data = super(SimpleInteractiveToolSerializer, self).validate(data)
        tool_type = data.get('tool_type')
        definition = data.get('definition', {})
        validate_sit_definition(tool_type=tool_type,
                                definition=definition)
        return data


class SimpleInteractiveToolTemplateSerializer(serializers.ModelSerializer):
    """
    This serializer is meant for importing / exporting courses that contain
    either links to existing SIT templates or need to create new SIT templates
    (that are then used by SITs in the course).
    """

    class Meta:
        model = SimpleInteractiveToolTemplate
        fields = ('author',
                  'tool_type',
                  'slug',
                  'name',
                  'description',
                  'instructions',
                  'definition',
                  'template_json')
        read_only_fields = ('id', 'author',)

    def create(self, validated_data):
        result = super().create(validated_data)
        return result

    def to_internal_value(self, data):
        slug = data.get('slug', None)
        if slug:
            try:
                template = SimpleInteractiveToolTemplate.objects.get(slug=slug)
                return template
            except SimpleInteractiveToolTemplate.DoesNotExist:
                pass
        result = super(SimpleInteractiveToolTemplateSerializer, self).to_internal_value(data)
        return result


class SimpleInteractiveToolSubmissionSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    simple_interactive_tool = serializers.PrimaryKeyRelatedField(required=True,
                                                                 queryset=SimpleInteractiveTool.objects.all())
    json_content = serializers.JSONField(allow_null=True)
    max_score = serializers.SerializerMethodField()

    class Meta:
        model = SimpleInteractiveToolSubmission
        fields = ('id', 'course', 'simple_interactive_tool', 'student', 'status', 'max_score', 'score', 'json_content')
        read_only_fields = ('id', 'status', 'score', 'max_score')

    def get_max_score(self, obj):
        """
        Return the max score possible for the user's submission.
        """
        return obj.simple_interactive_tool.max_score

    # noinspection PyUnresolvedReferences
    def validate(self, data):
        """
        Perform any SIT-specific validations here.
        """
        sit: SimpleInteractiveTool = data['simple_interactive_tool']

        # Make sure student can submit an answer for this course.
        course = data.get('course', None)
        student = self.context['request'].user
        if not user_is_enrolled(user=student, course=course):
            raise ValidationError(f"Student is not enrolled in this course")

        if course.has_finished:
            raise ValidationError("This course has finished. No further submissions are allowed.")

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # BASIC JSON_CONTENT CHECKS
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Size check
        json_content = data.get('json_content', None)
        data_size = sys.getsizeof(str(json_content))
        if data_size > settings.MAX_JSON_CONTENT_BYTES_ALLOWED:
            raise ValidationError("Too much data. Disallowed.")

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # VALIDATIONS FOR TOOL_TYPE : TABLETOOL
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if sit.tool_type == SimpleInteractiveToolType.TABLETOOL.name:
            if sit.definition:
                max_rows = sit.definition.get('max_rows', DEFAULT_MAX_TABLETOOL_ROWS_ALLOWED)
            else:
                max_rows = DEFAULT_MAX_TABLETOOL_ROWS_ALLOWED
            if json_content:
                if not isinstance(json_content, list):
                    logger.error(f"SimpleInteractiveToolSubmissionSerializer: Hmm. Weird. How did tabletool manage "
                                 f"to send data in a form other than list? Current user: {self.context['request'].user}")
                    raise ValidationError(f"Invalid data type.")

                if len(json_content) > max_rows:
                    raise ValidationError(f"Too many rows. Only {max_rows} allowed for this table.")

                # TODO: Make sure no cell with type 'STATIC' is changed and persisted.
                #  -> Updated STATIC values can be a security risk, because we parse the content as HTML...

        return data

    def create(self, validated_data):
        """
        Override ``create`` to provide a user via request.user by default.
        This is required since the read_only ``user`` field is not included by
        default anymore since https://github.com/encode/django-rest-framework/pull/5886.
        Therefore, we have to override create method in order to add in student user automatically via the request.user.
        We also write a tracking event for every SimpleInteractiveTool update.
        """

        # always make sure the submission is saved to the current user
        current_user = self.context['request'].user
        validated_data['student'] = current_user

        # This serializer is configured to accept course_unit.
        # Even though the SimpleInteractiveToolSubmission model doesn't have a relation to CourseUnit in the db,
        # the client passes in the current CourseUnit's ID in the 'course_unit' key when
        # a SimpleInteractiveTool is submitted.
        # We pop it off here if present and look up the CourseUnit, mainly so we can pass it
        # to the Tracker so that it has more data to track.
        course_unit_id = validated_data.pop('course_unit', None)

        try:
            tool_submission = super(SimpleInteractiveToolSubmissionSerializer, self).create(validated_data)
        except Exception as e:
            logger.error(f"SimpleInteractiveToolSubmissionSerializer : create(): "
                         f"validated_data: {validated_data} e: {e}")
            error_msg = f" Error saving SimpleInteractiveTool : {e}."
            raise serializers.ValidationError(error_msg)

        tool_submission.set_status()

        logger.info(f"SIT submission created : {tool_submission}")

        if tool_submission.status == SimpleInteractiveToolSubmissionStatus.COMPLETE.name:
            track_milestone_progress.apply_async(
                args=[],
                kwargs={
                    "course_id": tool_submission.course.id,
                    "user_id": tool_submission.student.id,
                    "block_uuid": tool_submission.simple_interactive_tool.block.uuid,
                    "submission_id": tool_submission.id,
                },
            )

        # Do event tracking in async task...
        track_simple_interactive_tool_submission.apply_async(
            args=[],
            kwargs={
                'simple_interactive_tool_submission_id': tool_submission.id,
                'course_unit_id': course_unit_id,
                'previous_simple_interactive_tool_status': None
            },
            # Use countdown to make sure DB transaction went through
            # before starting task...
            countdown=3)

        return tool_submission

    def update(self, instance: SimpleInteractiveToolSubmission, validated_data):

        # always make sure the submission is saved to the current user
        current_user = self.context['request'].user
        validated_data['student'] = current_user

        previous_status = instance.status
        try:
            tool_submission = super(SimpleInteractiveToolSubmissionSerializer, self).update(instance, validated_data)
        except Exception as e:
            logger.error(
                f"SimpleInteractiveToolSubmissionSerializer : create(): validated_data: {validated_data} e: {e}")
            error_msg = f" Error saving SimpleInteractiveTool : {e}."
            raise serializers.ValidationError(error_msg)

        tool_submission.set_status()

        logger.info(f"SIT submission updated : {tool_submission}")

        # This serializer is configured to accept course_unit.
        # Even though the SimpleInteractiveToolSubmission model doesn't have a relation to CourseUnit in the db,
        # the client passes in the current CourseUnit's ID in the 'course_unit' key when
        # a SimpleInteractiveTool is submitted.
        # We pop it off here if present and look up the CourseUnit, mainly so we can pass it
        # to the Tracker so that it has more data to track.
        course_unit_id = validated_data.pop('course_unit', None)

        if tool_submission.status == SimpleInteractiveToolSubmissionStatus.COMPLETE.name:
            track_milestone_progress.apply_async(
                args=[],
                kwargs={
                    "course_id": tool_submission.course.id,
                    "user_id": tool_submission.student.id,
                    "block_uuid": tool_submission.simple_interactive_tool.block.uuid,
                    "submission_id": tool_submission.id,
                },
            )

        # Do event tracking in async task...
        track_simple_interactive_tool_submission.apply_async(
            args=[],
            kwargs={
                'simple_interactive_tool_submission_id': tool_submission.id,
                'course_unit_id': course_unit_id,
                'previous_simple_interactive_tool_status': previous_status
            },
            # Use countdown to make sure DB transaction went through
            # before starting task...
            countdown=3)

        return instance
