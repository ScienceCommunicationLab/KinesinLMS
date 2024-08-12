from django.forms import ModelForm

from kinesinlms.email_automation.models import EmailAutomationProvider


class EmailAutomationProviderForm(ModelForm):
    class Meta:
        model = EmailAutomationProvider
        fields = [
            'active',
            'type',
            'api_url',
            'tag_ids'
        ]
