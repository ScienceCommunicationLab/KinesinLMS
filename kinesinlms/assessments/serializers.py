import logging

from django.db import IntegrityError
from django.utils.html import strip_tags
from jsonschema import validate as validate_json
from rest_framework import serializers

from kinesinlms.assessments.errors import SubmittedAnswerMissingError, InvalidSubmittedAnswer, TooManyAttemptsError
from kinesinlms.assessments.models import Assessment, SubmittedAnswer, AnswerStatus, AssessmentType
from kinesinlms.assessments.tracking import track_answer_submission
from kinesinlms.course.tasks import track_milestone_progress
from kinesinlms.course.models import CourseUnit
from kinesinlms.course.utils_access import can_access_course
from kinesinlms.learning_library.models import LearningObjective
from kinesinlms.learning_library.schema import DONE_INDICATOR_ANSWER_SCHEMA, LONG_FORM_TEXT_ANSWER_SCHEMA, MULTIPLE_CHOICE_ANSWER_SCHEMA, POLL_ANSWER_SCHEMA

logger = logging.getLogger(__name__)


class AssessmentSerializer(serializers.ModelSerializer):
    """
    Serializes an Assessment, but only the information needed for the client to render it.
    Does not include details like solution_json, which shouldn't be sent to client.
    Important to have the 'id' field in this serializer, since the client will need that
    to send student answers back to the server.
    """

    answers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = ('id', 'question', 'answers')


class LearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = (
            "slug",
            "type",
            "description"
        )


class AssessmentAllDataSerializer(serializers.ModelSerializer):
    """
    Serializes *all* data in an Assessment, including the solution_json.
    """

    class Meta:
        model = Assessment
        fields = ('type',
                  'slug',
                  'question',
                  'question_as_statement',
                  'definition_json',
                  'solution_json',
                  'explanation',
                  'show_answer',
                  'show_slug',
                  'attempts_allowed',
                  'has_correct_answer',
                  'complete_mode',
                  'graded')

    def create(self, validated_data):
        """
        If the uuid is provided, this Assessment should already
        exist so just load it and return from library. Otherwise,
        create it.
        Arg:
            validated_data:

        Returns:
            Assessment instance
        """
        uuid = validated_data.get("uuid", None)
        if uuid:
            raise NotImplementedError("Importing by uuid is not implemented yet.")
        assessment = Assessment.objects.create(**validated_data)
        return assessment


class SubmittedAnswerSerializer(serializers.ModelSerializer):
    """
    This serializer handles incoming 'answers' submitted by students via a React-based
    assessment component from library.js.

    Note that we override the 'create' and 'update' methods here rather than in the SubmittedAnswerViewSet.
    I think there's some back and forth about which place is better. We're going with here in the
    serializer for the time being.

    We sometimes pass back some Assessment information to the API client, such as
    the assessment explanation if the answer is correct.

    """

    student = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    explanation = serializers.SerializerMethodField()

    # Non-model fields, don't forget to pop before validating
    course_unit = serializers.CharField(write_only=True)

    class Meta:
        model = SubmittedAnswer
        fields = ('id',
                  'assessment',
                  'course',
                  'student',
                  'json_content',
                  'status',
                  'explanation',
                  'course_unit')

    def get_explanation(self, instance):
        if instance.status == AnswerStatus.CORRECT.name or instance.status == AnswerStatus.COMPLETE.name:
            try:
                return instance.assessment.explanation
            except Exception:
                logger.error(f"Could not get assessment explanation for answer {instance}")
        else:
            return None

    def validate(self, data):
        """
        We check json here b/c we need access to a different property,
        "type", to know which schema to use when validating json_content.

        Args:
            data:

        Returns:
            validated data
        """

        try:
            course = data['course']
        except Exception:
            logger.exception("Couldn't get course type from incoming answer data")
            raise serializers.ValidationError("Missing course field")

        if course.has_finished:
            raise serializers.ValidationError("Course has finished. No further submissions are allowed.")

        current_user = self.context['request'].user
        if not can_access_course(user=current_user, course=course):
            logger.exception(f"User {current_user} can not view course {course} and therefore "
                             f"answer submission is denied.")
            raise serializers.ValidationError("You don't have access to this course")

        if not course.self_paced:
            # Need to make sure this course unit is available. We're assuming
            # the course itself is released because we called the can_access_course method above.
            course_unit_id = int(data['course_unit'])
            course_unit = CourseUnit.objects.get(id=course_unit_id)
            if not course_unit.is_released:
                raise serializers.ValidationError("This unit is not yet released.")

        try:
            assessment = data['assessment']
            assessment_type = assessment.type
        except Exception:
            logger.exception("Couldn't get assessment type from incoming answer data")
            raise serializers.ValidationError("Missing assessment type field")

        # Use JSON schema to make sure incoming JSON is in the shape
        # we expect for the current assessment type.
        if assessment_type == AssessmentType.POLL.name:
            schema = POLL_ANSWER_SCHEMA
        elif assessment_type == AssessmentType.MULTIPLE_CHOICE.name:
            schema = MULTIPLE_CHOICE_ANSWER_SCHEMA
        elif assessment_type == AssessmentType.DONE_INDICATOR.name:
            schema = DONE_INDICATOR_ANSWER_SCHEMA
        elif assessment_type == AssessmentType.LONG_FORM_TEXT.name:
            schema = LONG_FORM_TEXT_ANSWER_SCHEMA
        else:
            raise serializers.ValidationError(f"Unsupported assessment type: {assessment_type}")

        try:
            json_content = data['json_content']
            validate_json(json_content, schema)
        except Exception as e:
            logger.debug("Invalid answer JSON: {}".format(e))
            raise InvalidSubmittedAnswer("Invalid answer JSON")

        # ESCAPE ANSWER INPUT
        # Escape answer_json just in case somebody is being naughty.
        # We can't escape because input may be returned to be displayed in
        # textarea (therefore > becomes &gt; which is no good)
        # So instead of using e.g. django-bleach we just strip tags for now.
        # Meanwhile, React will handle escaping code on client.
        try:
            if assessment_type in [AssessmentType.POLL.name, AssessmentType.MULTIPLE_CHOICE.name]:
                answers = json_content.get('answer')
                if answers:
                    cleaned_answers = []
                    for answer in answers:
                        clean_answer = strip_tags(answer)
                        cleaned_answers.append(clean_answer)
                    json_content['answer'] = cleaned_answers
            elif assessment_type == AssessmentType.LONG_FORM_TEXT.name:
                json_content = data['json_content']
                answer = json_content.get('answer', None)
                if answer:
                    clean_answer = strip_tags(answer)
                    data['json_content']['answer'] = clean_answer
        except Exception:
            logger.exception(f"Could not escape assessment answer input. data {data}")
            raise InvalidSubmittedAnswer("Invalid answer.")

        return data

    def create(self, validated_data):
        """
        Override ``create`` to provide a user via request.user by default.
        This is required since the read_only ``user`` field is not included by
        default anymore since https://github.com/encode/django-rest-framework/pull/5886.

        Therefore, we have to override create method in order to add in student user automatically via the request.user.
        See this issue: https://github.com/encode/django-rest-framework/issues/6031 for more details.

        We also write a tracking event for every answer created  and update progress against milestones.
        """
        current_user = self.context['request'].user
        validated_data['student'] = current_user

        # Even though the Answer model doesn't have a relation to CourseUnit in the db,
        # the client passes in the current CourseUnit's id as 'course_unit' when an Answer is submitted.
        # This serializer is configured to accept course_unit. We pop it off here if present and look up the
        # CourseUnit, mainly so we can pass it to the Tracker so that it has more data to track.
        course_unit_id = validated_data.pop('course_unit')
        course_unit = None
        if course_unit_id:
            try:
                course_unit = CourseUnit.objects.get(pk=course_unit_id)
            except CourseUnit.DoesNotExist:
                logger.error(f"Could not find course_unit by id {course_unit_id} passed from client.")

        try:
            answer = super().create(validated_data)
        except TooManyAttemptsError:
            error_msg = f"TooManyAttemptsError validated_data: {validated_data}."
            logger.exception(error_msg)
            raise serializers.ValidationError(error_msg)
        except SubmittedAnswerMissingError:
            error_msg = "Please submit an answer"
            raise serializers.ValidationError(error_msg)
        except IntegrityError:
            # Shouldn't have gotten here, since client would have done a PUT if this is an update.
            # Furthermore, the serializer should have returned a message like "The fields student, assessment,
            # course must make a unique set" if the client did do a POST. Alas, here we are.
            # Sentry has this bug now. Perhaps student clicked twice fast, causing two requests?...or had
            # two browser tabs open and used an old one after updating in the newer?
            logger.warning(f"Got that STRANGE INTEGRITY ERROR when trying to save student answer "
                           f"for validated_data: {validated_data}.")
            raise serializers.ValidationError("Internal error. Could not save answer. "
                                              "Please refresh the page and try again.")

        try:
            answer_status = answer.update_status()
        except Exception as e:
            logger.exception(f"Could not update answer status: {e}")
            raise serializers.ValidationError("Could not save status")
        logger.debug(f"Answer {answer} now has status {answer_status}")

        # Track before doing milestone, in case there's an error
        track_answer_submission(answer, course_unit=course_unit)

        # If this is a 'create' the answer status is new,
        # so having it unanswered is like doing nothing at all,
        # Only check status if something else happened.
        if answer.status != AnswerStatus.UNANSWERED.name:
            track_milestone_progress.apply_async(
                args=[],
                kwargs={
                    "course_id": answer.course.id,
                    "user_id": answer.student.id,
                    "block_uuid": answer.assessment.block.uuid,
                    "submission_id": answer.id,
                    "previous_answer_status": AnswerStatus.UNANSWERED.name,
                },
            )
        return answer

    def update(self, instance, validated_data):
        """
        Override update so that we can add a tracking event and
        update progress against milestones.

        Args:
            instance:
            validated_data:

        Returns:
            Updated instance
        """

        current_user = self.context['request'].user
        previous_answer_status = instance.status
        submitted_answer = None
        if current_user != instance.student:
            msg = f"Current user {current_user} tried editing " \
                  f"answer {instance} originally created by {instance.student}"
            logger.error(msg)
            raise serializers.ValidationError("Can't edit answer by a different student")

        try:
            submitted_answer = super().update(instance, validated_data)
        except TooManyAttemptsError:
            error_msg = f"Only {submitted_answer.assessment.attempts_allowed} submissions " \
                        f"allowed for this assessment."
            raise serializers.ValidationError(error_msg)
        except SubmittedAnswerMissingError:
            error_msg = "Please submit an answer"
            raise serializers.ValidationError(error_msg)

        if not submitted_answer:
            logger.error(f"#SubmittedAnswerSerializer: update() could not update instance: {instance} "
                         f"with validated_data {validated_data}. submitted_answer was None.")
            return instance

        # Allow exception to escape if there's an issue updating
        # the status of the answer...the client will handle it.
        answer_status = submitted_answer.update_status()
        logger.debug(f"Answer {submitted_answer} now has status {answer_status}")

        # Track *before* doing milestone, so we have a record of the answer
        # in case there's an error setting Milestone.
        try:
            track_answer_submission(submitted_answer, previous_answer_status=previous_answer_status)
        except Exception:
            # fail silently
            logger.exception("#SubmittedAnswerSerializer: update(). Succesfully updated answer but had an exception "
                             "when calling to track_answer_submission()")

        # Update the milestone counters, if applicable.
        if submitted_answer.status != AnswerStatus.UNANSWERED.name:
            try:
                track_milestone_progress.apply_async(
                    args=[],
                    kwargs={
                        "course_id": submitted_answer.course.id,
                        "user_id": submitted_answer.student.id,
                        "block_uuid": submitted_answer.assessment.block.uuid,
                        "submission_id": submitted_answer.id,
                        "previous_answer_status": previous_answer_status,
                    },
                )
            except Exception:
                logger.exception(f"Could not update milestone for answer {submitted_answer} ")
                # TODO :
                #   How should we handle submission if we can't track progress?
                #   Should we still allow?

        return instance
