import logging

from django.core.management import BaseCommand

from kinesinlms.badges.service import BadgrBadgeService
from kinesinlms.badges.models import BadgeProvider

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Refreshes the Badgr API key. Meant to be called from a cron job.

    """
    help = "Refresh the Badgr API key."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        logger.info(f"Refreshing Badgr token...")
        badge_provider = BadgeProvider.objects.get(slug="BADGR")
        service = BadgrBadgeService(badge_provider=badge_provider)
        try:
            service.refresh_token()
            logger.info(f"  - successfully refreshed Badgr token.")
        except Exception:
            # Logging the exception will be enough to get
            # an email via Sentry...
            logger.exception(f"Cannot refresh BADGR token")

