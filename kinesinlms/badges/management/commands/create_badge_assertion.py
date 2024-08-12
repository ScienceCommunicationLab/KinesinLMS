import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from kinesinlms.badges.models import BadgeClass, BadgeClassType
from kinesinlms.badges.utils import get_badge_service
from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Create a badge assertion for a particular user in a particular course."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser):
        parser.add_argument('--course', type=str)
        parser.add_argument('--username', type=str)

    def handle(self, *args, **options):
        token = options['token']
        username = options['username']
        user = User.objects.get(username=username)
        logger.info(f"Creating badge assertion for username {username} in course {token}")
        slug, run = token.split("_")
        course = Course.objects.get(slug=slug, run=run)
        badge_class = BadgeClass.objects.get(course=course,
                                             type=BadgeClassType.COURSE_PASSED.name)

        badge_service = get_badge_service()
        try:
            badge_assertion = badge_service.issue_badge_assertion(recipient=user, badge_class=badge_class, do_async=False)
            logger.info(f"  - Created badge assertion : {badge_assertion}")
        except Exception:
            logger.exception(f"  - ERROR creating badge assertion")
