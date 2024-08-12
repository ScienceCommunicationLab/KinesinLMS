import factory
from django.conf import settings

from kinesinlms.email_automation.constants import EmailAutomationProviderType
from kinesinlms.email_automation.models import EmailAutomationProvider


class EmailAutomationProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailAutomationProvider

    type = EmailAutomationProviderType.ACTIVE_CAMPAIGN.name
    active = True
    api_url = settings.TEST_EMAIL_AUTOMATION_PROVIDER_URL
