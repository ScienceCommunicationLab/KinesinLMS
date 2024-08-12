import logging

from django import forms
from django.core.exceptions import ValidationError
from django.forms import HiddenInput

from kinesinlms.course.models import Milestone, Course

logger = logging.getLogger(__name__)


class MilestoneForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        model = Milestone
        fields = [
            'required_to_pass',
            'course',
            'type',
            'slug',
            'name',
            'description',
            'count_requirement',
            'count_graded_only',
            'min_score_requirement',
            'badge_class']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk is None:
            # This is a CREATE. Check that the course doesn't already have a milestone of this type.
            course = cleaned_data['course']
            # You can only have one type for graded milestones
            milestone_type = cleaned_data['type']
            if course.milestones.filter(type=milestone_type).exists():
                raise ValidationError(f"You already defined a 'graded' milestone of type '{milestone_type}' "
                                      f"type within this course. You can only have "
                                      f"one 'graded' milestone of each type per course.")

        # Check that either count_requirement or min_score_requirement is set, but not both
        if cleaned_data["count_requirement"] and cleaned_data["min_score_requirement"]:
            raise ValidationError("Please set a count requirement OR a minimum total score, but not both.")

        return cleaned_data
