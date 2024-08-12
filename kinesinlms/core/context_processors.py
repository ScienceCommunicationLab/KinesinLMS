import logging

from kinesinlms.forum.utils import get_forum_provider

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
def site_context(request):
    """
    Add properties from models associated with Site to the context.
    Do not add secrets or sensitive information.
    """
    extra_context = {}
    try:
        current_site_forum_provider = get_forum_provider()
        if current_site_forum_provider and current_site_forum_provider.forum_url:
            extra_context['forum_url'] = current_site_forum_provider.forum_url
    except Exception:
        logger.exception("site_context() could not set context")

    return extra_context
