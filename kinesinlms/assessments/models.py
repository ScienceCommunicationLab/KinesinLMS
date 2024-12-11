import logging
import textwrap
import uuid
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _
from django_react_templatetags.mixins import RepresentationMixin
from jsonschema import validate

from kinesinlms.composer.enum import AssessmentCompleteMode
from kinesinlms.core.models import Trackable
from kinesinlms.course.models import Course
from kinesinlms.learning_library.constants import AnswerStatus, AssessmentType
from kinesinlms.learning_library.models import Block
from kinesinlms.learning_library.schema import (
    DONE_INDICATOR_DEFINITION_SCHEMA,
    MULTIPLE_CHOICE_DEFINITION_SCHEMA,
    MULTIPLE_CHOICE_SOLUTION_SCHEMA,
    POLL_DEFINITION_SCHEMA,
)

logger = logging.getLogger(__name__)


class Assessment(RepresentationMixin, Trackable):
    """
    An Assessment is a special kind of block that has both the question content
    and, if applicable, the correct answer details for that question.

    We have to be careful to never send the correct answer information to the
    client, only use it to validate incoming answers on the server. That's why
    we take the extra precaution of splitting definition json from solution json.

    Actual student answers to Assessments are stored in the Answer model, not here.


    """

    # TODO: Do we want to ensure that Assessments can only appear in a
    # TODO: Course not in Pathway or as a PublicResource?

    label = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("A label for the assessment."),
    )

    block = models.OneToOneField(
        Block,
        on_delete=models.CASCADE,
        related_name="assessment",
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in AssessmentType],
        default=None,
        null=True,
        blank=True,
    )

    slug = models.SlugField(
        null=True,
        blank=True,
        unique=False,
        allow_unicode=True,
    )

    # Question text to be shown above student input
    question = models.TextField(null=True, blank=True)

    # Question as statement, to be used for things like printable review.
    # e.g. if the question is
    #           Q3: What experimental techniques are you most interested in applying to your research and why?
    # this field might be
    #           The experimental techniques that I am most interested in applying to my research and why.
    question_as_statement = models.TextField(null=True, blank=True)

    # ASSESSMENT DEFINITION
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Holds unstructured data that defines this kind of assessment type. This
    # data includes information needed by front-end client to render assessment
    # and handle interactions.
    definition_json = JSONField(null=True, blank=True)

    # Holds unstructured correct answer information for this assessment
    # We keep this separate from definition_json to avoid sending to client by mistake.
    solution_json = JSONField(null=True, blank=True)

    # An extra explanation to show after question has been answered.
    # (If we need more granular explanations, we can extend solution_json
    # to support them.)
    explanation = models.TextField(null=True, blank=True)

    # If this is set, the client is allowed to show the correct answer
    # to the student at some point. Logic for that should be defined elsewhere,
    # this just indicates whether it's possible or not.
    show_answer = models.BooleanField(default=True, null=False, blank=True)

    # Indicates whether to show slug before assessment name when rendered in course Unit page.
    show_slug = models.BooleanField(default=True, null=False, blank=True)

    complete_mode = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in AssessmentCompleteMode],
        default=AssessmentCompleteMode.DISABLED_ON_COMPLETE.name,
        null=False,
        blank=False,
        help_text="Describes how an Assessment behaves when a student completes it.",
    )

    # How many times a student can submit an answer. Setting this
    # to `None` means there's no limit to attempts.
    attempts_allowed = models.IntegerField(default=None, null=True, blank=True)

    # ANSWER DEFINITION
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Indicates whether this assessment has a 'correct' answer or not
    # (Lots of assessments might not have a 'correct' answer...)
    has_correct_answer = models.BooleanField(default=False, null=True, blank=True)

    # If an assessment is 'graded' it means it counts towards
    # a milestone defined as a certain number of assessments to be completed.
    graded = models.BooleanField(default=False, null=False, blank=True)

    # Maximum score that can be earned for this Assessment.
    max_score = models.PositiveIntegerField(default=1, null=False, blank=False)

    def clean(self):
        if self.slug == "" or self.slug is None:
            self.slug = self.generate_generic_slug()

        if self.definition_json:
            # Make sure JSON fields have correct structure. Each type of assessment
            # should have its own JSON SCHEMA defined to be used for validation.
            try:
                if self.type == AssessmentType.DONE_INDICATOR.name:
                    validate(self.definition_json, DONE_INDICATOR_DEFINITION_SCHEMA)
                elif self.type == AssessmentType.POLL.name:
                    validate(self.definition_json, POLL_DEFINITION_SCHEMA)
                elif self.type == AssessmentType.MULTIPLE_CHOICE.name:
                    if self.definition_json.get("choices", None):
                        # If we have 'choices' in definition_json, we should use the MULTIPLE_CHOICE_DEFINITION_SCHEMA
                        validate(self.definition_json, MULTIPLE_CHOICE_DEFINITION_SCHEMA)
                        validate(self.solution_json, MULTIPLE_CHOICE_SOLUTION_SCHEMA)
                elif self.type == AssessmentType.LONG_FORM_TEXT.name:
                    # No use of definition_json yet for this type.
                    # If we do start to use definition_json for LFTE assessments,
                    # implement a LONG_FORM_TEXT_SCHEMA and uncomment line below.
                    # validate(self.definition_json, LONG_FORM_TEXT_SCHEMA)
                    pass
            except Exception as e:
                raise ValidationError("Invalid JSON: {}".format(e))

    def generate_generic_slug(self):
        slug = f"assessment_id_{uuid.uuid1()}"
        return slug

    @property
    def id_for_cc(self) -> str:
        """
        Returns a unique identifier for this assessment that is
        safe for use in Common Cartridge export files.

        Returns:
            str
        """
        # Give this the same uuid as the block,
        # as that's what we'll need to link correctly in the CC output.
        return str(self.block.uuid)

    @property
    def complete_json(self) -> Dict:
        """
        Returns a dict that includes both the definition and
        the solution data.

        This is used by things like Composer when we want to
        display a rich control for editing things like
        multiple choice options.

        Returns:
            dict
        """
        return {"definition": self.definition_json, "solution": self.solution_json}

    @complete_json.setter
    def complete_json(self, value):
        """
        Setter for complete_json. This is used by things like
        Composer when we want to display a rich control for
        editing things like multiple choice options.

        Note: This method does not validating incoming json.
        It expects clean() will be run before saving.

        Args:
            value: dict
        """
        self.definition_json = value["definition"]
        self.solution_json = value["solution"]

    def to_react_representation(self, context=None) -> Dict:
        """
        This method is used by our django-react-templatetags plugin.
        It shapes the model data for inclusion in the React component
        when included as part of a Django template. The React component
        then reads this data on startup.

        Therefore, this method should return an object that has
        everything React component needs to render the assessment.

        :param context:
        :return:
        """

        student = context["user"]
        course = context.get("course")
        course_unit = context.get("course_unit", None)
        if course_unit:
            course_unit_id = course_unit.id
            course_unit_slug = course_unit.slug
        else:
            course_unit_id = None
            course_unit_slug = None

        # Check for existing answer
        existing_submitted_answer = None
        try:
            existing_submitted_answer = SubmittedAnswer.objects.get(
                student=student, course=course, assessment_id=self.id
            )
        except SubmittedAnswer.DoesNotExist:
            pass
        except Exception as e:
            logger.exception(f"Error trying to get existing answer to assessment {self}. error: {e}")

        if existing_submitted_answer:
            existing_submitted_answer_json = {
                "id": existing_submitted_answer.id,
                "status": existing_submitted_answer.status,
                "json_content": existing_submitted_answer.json_content,
            }
            if existing_submitted_answer.status in [AnswerStatus.COMPLETE.name, AnswerStatus.CORRECT.name]:
                try:
                    existing_submitted_answer_json["explanation"] = self.explanation
                except Exception:
                    logger.exception("Could not attach 'explanation' to assessment details")
        else:
            existing_submitted_answer_json = None

        # javascript-like keys for react to use...
        obj = {
            "assessmentID": self.id,
            "type": self.type,
            "showAnswer": self.show_answer,
            "graded": self.graded,
            "definition": self.definition_json,
            "courseID": course.id,
            "courseUnitID": course_unit_id,
            "courseUnitSlug": course_unit_slug,
            "existingSubmittedAnswer": existing_submitted_answer_json,
        }

        # WARNING: Make sure not to send solution_json to client!!
        if "solution_json" in obj:
            logger.error("How did 'solution_json' get in response? Removing...")
            obj.pop("solution_json")

        return obj

    def __str__(self):
        if self.question:
            question = textwrap.shorten(self.question, 20, placeholder="...")
            return "{}. {} : {} ".format(self.id, self.type, question)
        else:
            return "{}. {} : {} ".format(self.id, self.type, self.slug)


class SubmittedAnswer(Trackable):
    """
    Holds a student's submitted answer to an assessment presented
    within one or more CourseUnits in a running Course.

    Submitted answer is stored in json_content. (Someday we may hold
    some answers in html_content, e.g. rich text for long-form text answers.)

    Important:  The student answer stored here is not necessarily the correct answer!
                The correct answer is defined in the Assessment model.
    """

    class Meta:
        unique_together = (("student", "assessment", "course"),)

    course = models.ForeignKey(Course, null=True, related_name="answers", on_delete=models.CASCADE)

    assessment = models.ForeignKey(
        Assessment, blank=False, null=False, related_name="answers", on_delete=models.CASCADE
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=False, null=False, related_name="answers", on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in AnswerStatus],
        default=AnswerStatus.UNANSWERED.value,
        null=False,
        blank=True,
    )

    attempts = models.IntegerField(default=1, null=False, blank=True)

    # Score achieved by the student (<= Assessment.max_score)
    score = models.PositiveIntegerField(default=1, null=False, blank=True)

    # All submitted answers are stored in the json field
    json_content = JSONField(null=True, blank=True)

    # My intention originally was to store long-form text answers
    # in a html field, but I never did so (using the json field instead).
    # So as of now, no answers are being stored in this field,
    # although I may use it later if we transition to rich text for long form answers...
    html_content = models.TextField(null=True, blank=True)

    def update_status(self) -> str:
        """
        Determine if submitted answer is correct, not
        correct, complete, incomplete or something else allowed by AnswerStatus.

        Set the 'status' property of this answer but does not save! ( A view
        or serializer might want to do something after updating status but
        before saving.)

        Returns:
            AnswerStatus enum name
        """

        # POLLS are, by definition, 'complete' if they have an answer
        if self.assessment.type == AssessmentType.POLL.name:
            if self.answer is not None:
                self.status = AnswerStatus.COMPLETE.name
            else:
                self.status = AnswerStatus.INCOMPLETE.name

        # DONE INDICATOR
        elif self.assessment.type == AssessmentType.DONE_INDICATOR.name:
            if self.answer:
                self.status = AnswerStatus.COMPLETE.name
            else:
                self.status = AnswerStatus.INCOMPLETE.name

        # LONG_FORM_TEXT
        # We have no way of deciding whether a long form text entry is correct
        # or incorrect, so we just mark them as COMPLETE or INCOMPLETE.
        elif self.assessment.type == AssessmentType.LONG_FORM_TEXT.name:
            # any entry is always complete
            if self.answer and len(self.answer) > 0:
                self.status = AnswerStatus.COMPLETE.name
            else:
                self.status = AnswerStatus.INCOMPLETE.name

        # MULTIPLE_CHOICE
        elif self.assessment.type == AssessmentType.MULTIPLE_CHOICE.name:
            logger.debug("handling multiple choice answers...")
            correct_choice_keys = self.assessment.solution_json["correct_choice_keys"]
            # Assume AND join if not defined. (Answers with only one option are default AND.)
            answer_join = self.assessment.solution_json.get("join", "AND")

            if answer_join == "AND":
                if set(self.answer) == set(correct_choice_keys):
                    self.status = AnswerStatus.CORRECT.name
                else:
                    self.status = AnswerStatus.INCORRECT.name

            elif answer_join == "OR":
                if set(self.answer).issubset(set(correct_choice_keys)):
                    self.status = AnswerStatus.COMPLETE.name
                else:
                    self.status = AnswerStatus.INCORRECT.name

        else:
            raise Exception("Unsupported assessment type {}".format(self.assessment.type))

        # Award the full score for complete or correct Answers
        if self.status in [AnswerStatus.COMPLETE.name, AnswerStatus.CORRECT.name]:
            self.score = self.assessment.max_score

        self.save()
        return self.status

    @property
    def disabled(self) -> bool:
        """
        Convenience function to determine if this answer is disabled or not.
        """
        if self.assessment.complete_mode == AssessmentCompleteMode.ALWAYS_ENABLED.name:
            return False
        elif self.assessment.complete_mode == AssessmentCompleteMode.DISABLED_ON_COMPLETE.name:
            return self.status in [AnswerStatus.COMPLETE.name, AnswerStatus.CORRECT.name]
        else:
            logger.warning(f"Unexpected complete_mode {self.assessment.complete_mode} for assessment {self.assessment}")
            return False

    @property
    def answer(self) -> Optional[Any]:
        """
        Convenience function to get answer information from this model's
        json_content field, in the shape expected for this assessment's
        type field.

        Returns:
            text of submitted answer.
        """

        # DMcQ: All assessments use the json_content field
        # Later we may do something like:
        #     if self.assessment.type == AssessmentType.LONG_FORM_TEXT.name:
        #          answer = self.html_content
        #      else:
        #          .....

        if not hasattr(self, "json_content") or self.json_content is None:
            if self.assessment.type == AssessmentType.DONE_INDICATOR.name:
                return False
            else:
                return None

        answer = self.json_content.get("answer", None)
        if answer == "":
            if self.assessment.type == AssessmentType.DONE_INDICATOR.name:
                answer = False
            else:
                answer = None

        return answer

    @answer.setter
    def answer(self, value):
        """
        Record the user's answer in the json_content field
        in a way that makes sense for the current assessment type field.
        """
        if not hasattr(self, "json_content"):
            self.json_content = {}
        if not hasattr(self.json_content, "answer"):
            self.json_content = {"answer": None}
        if self.assessment.type == AssessmentType.LONG_FORM_TEXT.name:
            self.json_content["answer"] = value
        elif self.assessment.type == AssessmentType.DONE_INDICATOR.name:
            self.json_content["answer"] = value is True
        elif self.assessment.type == AssessmentType.MULTIPLE_CHOICE.name:
            if isinstance(value, str):
                value = [value]
            self.json_content["answer"] = value
        else:
            raise NotImplementedError()

    def get_answer_data_for_tracking_log(self):
        return {
            "assessment_id": self.assessment.id,
            "assessment_type": self.assessment.type,
            "answer_id": self.id,
            "status": self.status,
            "attempts": self.attempts,
            "json_content": self.json_content,
            "html_content": self.html_content,
        }

    def __str__(self):
        return "Submitted answer id: {}".format(self.id)
