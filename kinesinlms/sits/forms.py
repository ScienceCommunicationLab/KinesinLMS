from crispy_forms.helper import FormHelper
from django.forms import ModelForm

from kinesinlms.sits.models import SimpleInteractiveToolTemplate, SimpleInteractiveTool


class SimpleInteractiveToolForm(ModelForm):
    class Meta:
        model = SimpleInteractiveTool
        fields = ['name',
                  'tool_type',
                  'slug',
                  'instructions',
                  'definition']


class SimpleInteractiveToolTemplateForm(ModelForm):
    class Meta:
        model = SimpleInteractiveToolTemplate
        fields = ['name', 'tool_type', 'description', 'instructions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
