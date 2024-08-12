from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.widgets import HiddenInput

from kinesinlms.course.models import Cohort


class CohortForm(ModelForm):
    class Meta:
        model = Cohort
        fields = [
            'course',
            'name',
            'slug',
            'institution',
            'tags',
            'description'
        ]
        widgets = {
            'course': HiddenInput,
        }

    def clean(self):
        cleaned_data = self.cleaned_data

        if cleaned_data['slug'] == "DEFAULT":
            raise ValidationError("You cannot use 'DEFAULT' as a slug.")

        if not self.instance:
            # This is a new creation
            if Cohort.objects.filter(course=cleaned_data['course'], slug=cleaned_data['slug']).exists():
                raise ValidationError('A cohort with this slug already exists for this course')

            if Cohort.objects.filter(course=cleaned_data['course'], slug=cleaned_data['name']).exists():
                raise ValidationError('A cohort with this name already exists for this course')

        return cleaned_data
