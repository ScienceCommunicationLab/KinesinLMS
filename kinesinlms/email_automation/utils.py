from typing import Optional

from django.contrib.sites.models import Site

from kinesinlms.email_automation.constants import EmailAutomationProviderType
from kinesinlms.email_automation.service import ActiveCampaignService


def get_email_automation_service() -> Optional["kinesinlms.email_automation.service.EmailAutomationService"]:
    email_automation_provider = get_email_automation_provider()
    if email_automation_provider:
        if email_automation_provider.type == EmailAutomationProviderType.ACTIVE_CAMPAIGN.name:
            return ActiveCampaignService(provider=email_automation_provider)
        # Add more conditions for other email automation providers here...
        else:
            raise ValueError("Invalid email automation provider")
    return None


def get_email_automation_provider() -> Optional["kinesinlms.email_automation.models.EmailAutomationProvider"]:
    site = Site.objects.get_current()
    email_automation_provider = getattr(site, 'email_automation_provider', None)
    return email_automation_provider

