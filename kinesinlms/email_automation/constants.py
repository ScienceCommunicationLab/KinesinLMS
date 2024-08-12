from enum import Enum


class EmailAutomationProviderType(Enum):
    """
    Types of email automation services supported by the system.
    """
    # Only one kind of email automation provider at the moment...
    ACTIVE_CAMPAIGN = "ActiveCampaign"
