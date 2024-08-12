import logging

from django import forms
from django.forms import ModelForm

from kinesinlms.learning_library.models import Resource

logger = logging.getLogger(__name__)


class ResourceForm(ModelForm):

    resource_file = forms.FileField(label="Select resource file",
                                    widget=forms.FileInput())

    class Meta:
        model = Resource
        fields = [
            'resource_file',
            'type',
            'description'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].widget.attrs['style'] = 'height: 3rem;'

