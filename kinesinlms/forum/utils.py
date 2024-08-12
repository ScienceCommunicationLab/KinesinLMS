import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site

from kinesinlms.core.constants import ForumProviderType

logger = logging.getLogger(__name__)

User = get_user_model()


def get_forum_service() -> (
    Optional["kinesinlms.forum.service.base_service.BaseForumService"]
):
    forum_provider = get_forum_provider()
    if forum_provider:
        if forum_provider.type == ForumProviderType.DISCOURSE.name:
            # Don't import the DiscourseForumService class unless we need it. Otherwise, we'll get circular import errors.
            from kinesinlms.forum.service.discourse_service import DiscourseForumService
            return DiscourseForumService(provider=forum_provider)
        # Add more conditions for other forum providers here...
        else:
            raise ValueError(
                "Invalid forum service provider. Only DISCOURSE ForumProviders is currently supported."
            )
    return None


def get_forum_provider() -> Optional["kinesinlms.forum.model.ForumProvider"]:
    site = Site.objects.get_current()
    forum_provider = getattr(site, "forum_provider", None)
    return forum_provider
