import logging

from pydiscourse.client import DiscourseClient as PyDiscourseClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ACTIVECAMPAIGN METHODS AND CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

logger = logging.getLogger(__name__)


class DiscourseClient(PyDiscourseClient):
    """
    Implments a client for the external Discourse forum.
    At the moment just using functionality defined in the pydiscourse client.
    In the future this class might replace that library as it doesn't provide
    that much functionality.
    """

    def __init__(self, host, api_username, api_key, timeout=None):
        super().__init__(host, api_username, api_key, timeout=timeout)
