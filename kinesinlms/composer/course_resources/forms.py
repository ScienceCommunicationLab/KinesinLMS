import logging

from django import forms
from django.forms import HiddenInput

from kinesinlms.course.models import Course, CourseResource
from kinesinlms.educator_resources.models import EducatorResource

logger = logging.getLogger(__name__)


class EducatorCourseResourceForm(forms.ModelForm):

    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=HiddenInput(),
    )

    file = forms.FileField(
        label='Resource File',
        required=True,
        help_text='Upload a file to be used as a resource in the course.')

    class Meta:
        model = EducatorResource
        fields = [
            'course',
            'enabled',
            'type',
            'name',
            'overview',
            'content',
            'file',
            'url'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class CourseResourceForm(forms.ModelForm):

    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=HiddenInput(),
    )

    resource_file = forms.FileField(
        label='Resource File',
        required=True,
        help_text='Upload a file to be used as a resource in the course.')

    class Meta:
        model = CourseResource
        fields = [
            'course',
            'name',
            'description',
            'resource_file'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # TODO: Cleans...

        return cleaned_data
