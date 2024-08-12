from django import forms
from django.contrib.auth import get_user_model

from kinesinlms.assessments.models import Assessment


class SelectSubmittedAnswersForm(forms.Form):

    def __init__(self, course, *args, **kwargs):
        """
        Add extra fields to allow selection of a student and/or assessment.
        """
        super().__init__(*args, **kwargs)

        User = get_user_model()
        self.fields["student"] = forms.ModelChoiceField(
            # Show only those users enrolled in this course.
            queryset=User.objects.order_by("username"),
            limit_choices_to={"enrollments__course": course, "enrollments__active": True},
            label="Student",
            required=False,
            empty_label="--- all ---",
        )

        self.fields["assessment"] = forms.ModelChoiceField(
            # Show only those Assessments that are in this course, in block order.
            queryset=Assessment.objects.order_by("block__unit_blocks__block_order"),
            limit_choices_to={"block__unit_blocks__course_unit__course": course},
            label="Assessment",
            required=False,
            empty_label="--- all ---",
        )

        # We have to call this directly because we're not using a ModelFormView
        forms.models.apply_limit_choices_to_to_formfield(self.fields["student"])
        forms.models.apply_limit_choices_to_to_formfield(self.fields["assessment"])
