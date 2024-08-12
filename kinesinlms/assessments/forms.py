import logging
from typing import Optional, List

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _

from kinesinlms.assessments.models import SubmittedAnswer, Assessment
from kinesinlms.composer.enum import AssessmentCompleteMode
from kinesinlms.course.models import Course, CourseUnit
from kinesinlms.learning_library.constants import AnswerStatus, BlockViewMode

logger = logging.getLogger(__name__)

User = get_user_model()


class SubmittedAnswerForm(forms.Form):
    """
    A base class for all submitted answer forms.
    Each type of assessment should subclass this form, e.g. DoneIndicatorForm
    """
    course_unit_id = forms.CharField(widget=forms.HiddenInput(), required=True)

    # This is used to track the previous answer when the form is saved.
    # Used for logging.
    previous_answer_status = None

    class Meta:
        fields = ['course_unit_id']

    def __init__(self, *args, assessment, student, course, **kwargs):

        self.block_view_context = kwargs.pop('block_view_context', None)
        self.block_view_mode = kwargs.pop('block_view_mode', None)

        try:
            submitted_answer = SubmittedAnswer.objects.get(student=student,
                                                           course=course,
                                                           assessment_id=assessment.id)
        except SubmittedAnswer.DoesNotExist:
            submitted_answer = None

        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        if args and 'answer' in args[0]:
            # This is a POST from the student.
            # We'll use passed in answer not saved answer.
            pass
        elif submitted_answer:
            kwargs['initial']['answer'] = submitted_answer.answer

        super().__init__(*args, **kwargs)

        if not assessment:
            raise ValueError("assessment must be provided.")
        if not student:
            raise ValueError("student must be provided.")
        if not course:
            raise ValueError("course must be provided.")

        self.submitted_answer: Optional[SubmittedAnswer] = submitted_answer
        self.previous_answer_status = submitted_answer.status if submitted_answer else None
        self.course: Course = course
        self.assessment: Assessment = assessment
        self.student: User = student

    # ~~~~~~~~~~~~~~~~~~~~~~
    # PROPERTIES
    # ~~~~~~~~~~~~~~~~~~~~~~

    @property
    def answer_status(self) -> str:
        if self.submitted_answer:
            return self.submitted_answer.status
        else:
            return AnswerStatus.UNANSWERED.name

    @property
    def answer_score(self) -> Optional[int]:
        if self.submitted_answer:
            return self.submitted_answer.score
        else:
            return None

    @property
    def is_assessment_disabled(self) -> bool:
        """
        The assessment might be disabled because of the state of the
        assessment, or because the block is being viewed in a different
        context (e.g. Composer).
        """
        if self.block_view_mode == BlockViewMode.READ_ONLY.name:
            return True

        if self.submitted_answer:
            return self.submitted_answer.disabled

        return False

    # ~~~~~~~~~~~~~~~~~~~~~~
    # METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~

    def clean(self):

        cleaned_data = super().clean()

        if self.submitted_answer and self.submitted_answer.status == AnswerStatus.COMPLETE.name and self.assessment.complete_mode == AssessmentCompleteMode.DISABLED_ON_COMPLETE.name:
            raise ValidationError("This assessment is already complete.")

        try:
            course_unit_id = cleaned_data['course_unit_id']
        except Exception as e:
            raise ValidationError("course_unit_id is required.") from e
        course_unit = CourseUnit.objects.get(id=course_unit_id, course=self.course)
        if not course_unit.is_released:
            raise ValidationError("This unit is not yet released.")
        return cleaned_data

    def save(self, *args, **kwargs) -> SubmittedAnswer:
        instance, created = SubmittedAnswer.objects.get_or_create(assessment=self.assessment,
                                                                  student=self.student,
                                                                  course=self.course)
        self.submitted_answer = instance

        self.submitted_answer.answer = self.cleaned_data['answer']
        self.submitted_answer.update_status()
        self.submitted_answer.save()
        return instance

    def disable(self):
        for field_name, field in self.fields.items():
            field.widget.attrs['disabled'] = True


class DoneIndicatorForm(SubmittedAnswerForm):
    answer = forms.BooleanField(required=False,
                                widget=forms.CheckboxInput())

    class Meta:
        fields = SubmittedAnswerForm.Meta.fields + ['answer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        default_indicator_text = _('I have completed this assessment.')

        if not self.assessment.definition_json:
            self.assessment.definition_json = {
                'indicator_text': default_indicator_text
            }

        self.fields['answer'].label = self.assessment.definition_json.get('done_indicator_label',
                                                                          default_indicator_text)

        if self.submitted_answer:
            self.fields['answer'].initial = self.submitted_answer.answer
            if self.is_assessment_disabled:
                self.fields['answer'].disabled = True

    # ~~~~~~~~~~~~~~~~~~~~~~
    # METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~

    def clean(self):
        cleaned_data = super().clean()
        # Transform any truthy value to True
        if 'answer' in cleaned_data:
            # Transform any truthy value to True
            cleaned_data['answer'] = cleaned_data['answer'] == True
        return cleaned_data

    def save(self, *args, **kwargs) -> SubmittedAnswer:
        super().save(*args, **kwargs)
        submitted_answer = self.submitted_answer
        submitted_answer.answer = self.cleaned_data['answer']
        submitted_answer.status = AnswerStatus.COMPLETE.name
        submitted_answer.save()
        self.submitted_answer = submitted_answer
        return self.submitted_answer


class PollForm(SubmittedAnswerForm):
    """
    Polls are just like MultipleChoiceForm except that they
    don't have a correct answer. They may evolve to have
    a wider set of options in the future, which is why
    they get a separate Form and template rather than
    just being a 'mode' of MultipleChoiceForm.
    """
    answer = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        fields = SubmittedAnswerForm.Meta.fields + ['answer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assessment = self.assessment
        definition_json = assessment.definition_json
        if definition_json:
            self.choices = definition_json.get('choices', [])
        else:
            self.choices = []
        multiple_choice_choices = [(choice['choice_key'], choice['text']) for choice in self.choices]
        self.fields['answer'].choices = multiple_choice_choices

    # ~~~~~~~~~~~~~~~~~~~~~~
    # PROPERTIES
    # ~~~~~~~~~~~~~~~~~~~~~~

    @property
    def selected_choices(self) -> List:
        """
        Use this method to set the selected choices when the form
        is first populated.
        """
        selected_choices = []
        if self.submitted_answer.answer:
            selected_choices = self.submitted_answer.answer
        return selected_choices

    @property
    def valid_choices(self) -> List:
        valid_choices = []
        if self.assessment and self.assessment.definition_json:
            return [
                item['choice_key']
                for item
                in self.assessment.definition_json['choices']
            ]
        return valid_choices

    # ~~~~~~~~~~~~~~~~~~~~~~
    # METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~

    def clean_answer(self) -> List[str]:
        answer = self.cleaned_data.get("answer", None)
        if answer is not None:
            if isinstance(answer, str):
                return [answer]
            elif isinstance(answer, list):
                return answer
            else:
                raise forms.ValidationError("Invalid data type for answer field.")
        else:
            return []

    def clean(self):
        cleaned_data = super().clean()
        selected_choices = cleaned_data.get('answer')
        invalid_choices = set(selected_choices) - set(self.valid_choices)
        if invalid_choices:
            raise ValidationError("Invalid answer.")

        return cleaned_data


class MultipleChoiceForm(SubmittedAnswerForm):
    answer = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        fields = SubmittedAnswerForm.Meta.fields + ['answer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assessment = self.assessment
        definition_json = assessment.definition_json
        if definition_json:
            self.choices = definition_json.get('choices', [])
        else:
            self.choices = []
        multiple_choice_choices = [(choice['choice_key'], choice['text']) for choice in self.choices]
        self.fields['answer'].choices = multiple_choice_choices

    # ~~~~~~~~~~~~~~~~~~~~~~
    # PROPERTIES
    # ~~~~~~~~~~~~~~~~~~~~~~

    @property
    def selected_choices(self) -> List:
        """
        Use this method to set the selected choices when the form
        is first populated.
        """
        selected_choices = []
        if self.submitted_answer.answer:
            selected_choices = self.submitted_answer.answer
        return selected_choices

    @property
    def valid_choices(self) -> List:
        valid_choices = []
        if self.assessment and self.assessment.definition_json:
            return [
                item['choice_key']
                for item
                in self.assessment.definition_json['choices']
            ]
        return valid_choices

    # ~~~~~~~~~~~~~~~~~~~~~~
    # METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~

    def clean_answer(self) -> List[str]:
        answer = self.cleaned_data.get("answer", None)
        if answer is not None:
            if isinstance(answer, str):
                return [answer]
            elif isinstance(answer, list):
                return answer
            else:
                raise forms.ValidationError("Invalid data type for answer field.")
        else:
            return []

    def clean(self):
        cleaned_data = super().clean()
        selected_choices = cleaned_data.get('answer')
        invalid_choices = set(selected_choices) - set(self.valid_choices)
        if invalid_choices:
            raise ValidationError("Invalid answer.")

        return cleaned_data


class LongFormTextEntryForm(SubmittedAnswerForm):
    answer = forms.CharField(widget=Textarea(attrs={'cols': 80, 'rows': 5}))

    class Meta:
        fields = SubmittedAnswerForm.Meta.fields + ['answer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.submitted_answer:
            self.fields['answer'].initial = self.submitted_answer.answer
        if self.is_assessment_disabled:
            self.fields['answer'].disabled = True
