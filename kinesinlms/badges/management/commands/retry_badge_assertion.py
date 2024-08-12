import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from kinesinlms.badges.models import BadgeAssertion
from kinesinlms.badges.utils import get_badge_service

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Retry a failed badge assertion."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser):
        parser.add_argument('--id', type=str)

    def handle(self, *args, **options):
        badge_id = options['id']
        badge_assertion = BadgeAssertion.objects.get(id=badge_id)
        badge_service = get_badge_service()
        print("Retrying badge assertion...")
        started = badge_service.retry_badge_assertion(badge_assertion)
        if started:
            print("  - Retry started.")
        else:
            print("  - Retry not started.")
