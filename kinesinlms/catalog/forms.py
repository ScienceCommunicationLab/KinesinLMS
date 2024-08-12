from django import forms

from kinesinlms.course.models import EnrollmentSurveyAnswer, EnrollmentSurveyQuestion, EnrollmentSurveyQuestionType


class EnrollmentSurveyAnswerForm(forms.ModelForm):
    class Meta:
        model = EnrollmentSurveyAnswer
        fields = ['answer']

    def __init__(self, *args, enrollment_question: EnrollmentSurveyQuestion, **kwargs):
        super().__init__(*args, **kwargs)
        if not enrollment_question:
            raise ValueError("enrollment_question must be defined when using multiple choice questions.")

        if enrollment_question.question_type == EnrollmentSurveyQuestionType.MULTIPLE_CHOICE.name:
            choices = [(item['key'], item['value']) for item in enrollment_question.definition]
            self.fields['answer'] = forms.ChoiceField(
                widget=forms.RadioSelect,
                required=True,
                label=enrollment_question.question,
                choices=choices)
        elif enrollment_question.question_type == EnrollmentSurveyQuestionType.TEXT.name:
            self.fields['answer'] = forms.CharField(required=True,
                                                    label=enrollment_question.question,
                                                    widget=forms.Textarea)
        else:
            raise Exception(f"Unsupported enrollment question type {enrollment_question.question_type}")
