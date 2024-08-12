from django.forms import ModelForm

from kinesinlms.survey.models import SurveyProvider


class SurveyProviderForm(ModelForm):
    class Meta:
        model = SurveyProvider
        fields = [
            'active',
            'name',
            'type',
            'slug',
            'datacenter_id',
            'callback_secret'
        ]
