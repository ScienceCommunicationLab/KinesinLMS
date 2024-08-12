import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site

from kinesinlms.badges.models import BadgeProviderType
from kinesinlms.badges.service import BadgrBadgeService

logger = logging.getLogger(__name__)

User = get_user_model()


def get_badge_service() -> Optional['kinesinlms.badges.service.BaseBadgeService']:
    badge_provider = get_badge_provider()
    if badge_provider:
        if badge_provider.type == BadgeProviderType.BADGR.name:
            return BadgrBadgeService(badge_provider=badge_provider)
        # Add more conditions for other forum providers here...
        else:
            raise ValueError("Invalid forum service provider. Only BADGR BadgeProviderType is currently supported.")
    return None


def get_badge_provider() -> Optional['kinesinlms.badges.model.BadgeProvider']:
    site = Site.objects.get_current()
    badge_provider = getattr(site, 'badge_provider', None)
    return badge_provider
